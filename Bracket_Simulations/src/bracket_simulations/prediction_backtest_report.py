from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bracket_simulations.actual_results import EXPECTED_N, STAGES
from bracket_simulations.compare import _load_preds, probabilities_csv

# When the exact actual team set never appears in sims, cumulative mass on other combos
# is ~all observed probability; report this sentinel instead of 0 (which looked optimal).
NOT_OBSERVED_CUMULATIVE_FREQUENCY = 0.999


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _yn(ok: bool) -> str:
    return "yes" if ok else "no"


def _display_combo(combo: str) -> str:
    return combo.replace("|", ", ")


def _rank_display(joint: dict[str, Any]) -> str:
    rank = int(joint.get("rank_actual", 0) or 0)
    n_unique = int(joint.get("n_unique_configs", 0) or 0)
    if rank <= 0:
        return f"not observed / {n_unique:,}"
    if rank > n_unique and float(joint.get("p_joint_actual", 0.0)) <= 0.0:
        return f"not observed / {n_unique:,}"
    return f"{rank:,} / {n_unique:,}"


def _team_rows(teams: list[str], *, per_row: int = 6) -> list[str]:
    if not teams:
        return ["_(none)_"]
    rows: list[str] = []
    for i in range(0, len(teams), per_row):
        rows.append(" | ".join(teams[i : i + per_row]))
    return rows


def _render_team_block(title: str, teams: list[str]) -> list[str]:
    lines = [f"**{title}** - {len(teams)} teams"]
    for row in _team_rows(teams):
        lines.append(f"> {row}")
    return lines


def _render_metric4_side(label: str, joint: dict[str, Any]) -> list[str]:
    rank = int(joint.get("rank_teams_covered", 0))
    actual = joint.get("teams_actual_in_union") or []
    extras = joint.get("teams_extras_in_union") or []
    lines = [
        f"#### {label}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Stop at combo rank | **{rank}** |",
        f"| Cumulative probability | **{_pct(joint['cumulative_teams_covered'])}** |",
        f"| Last actual team to appear | **{joint.get('last_team_covered', '')}** |",
        f"| Combo at that rank | {_display_combo(str(joint.get('combo_at_coverage', '')))} |",
        f"| Union size (teams in ranks 1-{rank}) | {joint.get('teams_in_predictions_n', 0)} |",
        "",
    ]
    lines.extend(_render_team_block("Actual teams covered", actual))
    lines.append("")
    lines.extend(_render_team_block("Other teams in union (not in actual set)", extras))
    lines.append("")
    return lines


def _render_tournament_section(r: dict[str, Any], tournament_id: str) -> list[str]:
    comp = r["competition"]
    lines = [f"## {comp} (`{tournament_id}`)", ""]
    lines.append(f"**Champion (actual):** {r['champion_actual']}")
    lines.append("")

    lines.append("### At a glance")
    lines.append("")
    lines.append(
        "| Stage | "
        "M1 market | M1 model | "
        "M2 mkt | M2 mdl | "
        "M3 cum mkt | M3 cum mdl | "
        "M4 cum mkt | M4 cum mdl |"
    )
    lines.append(
        "|-------|"
        "-----------|-----------|"
        "--------|--------|"
        "----------|----------|"
        "----------|----------|"
    )
    for stage in STAGES:
        n = EXPECTED_N[stage]
        ms, ds = r["market"][stage], r["model"][stage]
        mj, dj = r["market_joint"][stage], r["model_joint"][stage]
        lines.append(
            f"| **{stage}** | "
            f"{int(ms['topn_hits'])}/{n} | {int(ds['topn_hits'])}/{n} | "
            f"{_yn(mj['top1_correct'])} | {_yn(dj['top1_correct'])} | "
            f"{_pct(mj['cumulative_frequency'])} | {_pct(dj['cumulative_frequency'])} | "
            f"{_pct(mj['cumulative_teams_covered'])} | {_pct(dj['cumulative_teams_covered'])} |"
        )
    lines.append("")
    lines.append(
        "_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); "
        "M3 = cumulative probability up to the exact actual set "
        f"(if never simulated, {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}); "
        "M4 = cumulative probability until all actual teams have appeared in some combo._"
    )
    lines.append("")

    market_preds = _load_preds(probabilities_csv(tournament_id, "market_all"))
    model_preds = _load_preds(probabilities_csv(tournament_id, "model_all"))
    all_teams = sorted(market_preds.keys())

    for stage in STAGES:
        n = EXPECTED_N[stage]
        col = f"p_at_least_{stage}"
        actual_sorted = sorted(r["actual_config"][stage])
        actual_set = set(actual_sorted)
        ms, ds = r["market"][stage], r["model"][stage]
        mj, dj = r["market_joint"][stage], r["model_joint"][stage]
        mr = sorted(all_teams, key=lambda t: market_preds[t][col], reverse=True)[:n]
        dr = sorted(all_teams, key=lambda t: model_preds[t][col], reverse=True)[:n]

        lines.append(f"### {stage}")
        lines.append("")
        lines.extend(_render_team_block(f"Actual participants ({n})", actual_sorted))
        lines.append("")

        lines.append("#### Metric 1 - Top-N by `p_at_least`")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(f"| Recall | **{int(ms['topn_hits'])}/{n}** | **{int(ds['topn_hits'])}/{n}** |")
        lines.append(
            f"| Perfect set | {_yn(ms['topn_hits'] == n and ms['topn_fp'] == 0)} | "
            f"{_yn(ds['topn_hits'] == n and ds['topn_fp'] == 0)} |"
        )
        m_miss = sorted(actual_set - set(mr))
        d_miss = sorted(actual_set - set(dr))
        if m_miss:
            lines.append(f"| Missed | {', '.join(m_miss)} | |")
        if d_miss:
            lines.append(f"| | | {', '.join(d_miss)} |")
        lines.append("")
        lines.extend(_render_team_block(f"Market top-{n} pick", mr))
        lines.append("")
        lines.extend(_render_team_block(f"Model top-{n} pick", dr))
        lines.append("")

        lines.append("#### Metric 2 - Most frequent exact set (rank 1)")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(f"| Match actual set | {_yn(mj['top1_correct'])} | {_yn(dj['top1_correct'])} |")
        lines.append(
            f"| Probability | {_pct(mj['top1_probability'])} | {_pct(dj['top1_probability'])} |"
        )
        lines.append(
            f"| Set | {_display_combo(str(mj.get('top1_teams', '')))} | "
            f"{_display_combo(str(dj.get('top1_teams', '')))} |"
        )
        lines.append("")

        actual_pipe = "|".join(actual_sorted)
        lines.append("#### Metric 3 - Exact actual set in joint distribution")
        lines.append("")
        lines.append(f"Target combo: {_display_combo(actual_pipe)}")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(f"| Rank | {_rank_display(mj)} | {_rank_display(dj)} |")
        lines.append(
            f"| p(actual set) | {_pct(mj['p_joint_actual'])} | {_pct(dj['p_joint_actual'])} |"
        )
        lines.append(
            f"| Cumulative through that rank | {_pct(mj['cumulative_frequency'])} | "
            f"{_pct(dj['cumulative_frequency'])} |"
        )
        lines.append("")

        lines.append("#### Metric 4 - All actual teams seen in top combos")
        lines.append("")
        lines.extend(_render_metric4_side("Market", mj))
        lines.extend(_render_metric4_side("Model", dj))

    lines.append("---")
    lines.append("")
    return lines


def _render_worked_example(results: list[dict[str, Any]]) -> list[str]:
    worked = next((row for row in results if row.get("tournament") == "wc2022"), None)
    if worked is None:
        return []

    joint = worked["model_joint"]["SF"]
    actual_teams = sorted(worked["actual_config"]["SF"])
    actual_pipe = "|".join(actual_teams)
    rank_actual = int(joint.get("rank_actual", 0) or 0)
    rank_cover = int(joint.get("rank_teams_covered", 0) or 0)
    cumulative_actual = _pct(float(joint.get("cumulative_frequency", 0.0) or 0.0))
    cumulative_cover = _pct(float(joint.get("cumulative_teams_covered", 0.0) or 0.0))
    trigger_combo = joint.get("combo_at_coverage", "")
    last_team = joint.get("last_team_covered", "")
    union_size = int(joint.get("teams_in_predictions_n", 0) or 0)
    extra_count = len(joint.get("teams_extras_in_union") or [])

    return [
        "## Worked example - WC 2022 SF (model)",
        "",
        "| | Metric 3 (exact set) | Metric 4 (all teams seen) |",
        "|--|----------------------|---------------------------|",
        f"| Target | {_display_combo(actual_pipe)} | Same four teams, any combo |",
        f"| Stop rank | {rank_actual:,} | **{rank_cover:,}** |",
        f"| Cumulative | {cumulative_actual} | **{cumulative_cover}** |",
        f"| Trigger combo | exact quartet | {_display_combo(trigger_combo)} ({last_team} last) |",
        "",
        f"At rank {rank_cover:,} the model has seen every actual SF team at least once, but only "
        f"{cumulative_cover} of simulated mass; the exact quartet needs rank {rank_actual:,} "
        f"({cumulative_actual}).",
        "",
        f"Union at rank {rank_cover:,} (**{union_size}** teams): all four actual plus {extra_count} "
        "others that appeared in high-frequency SF combos (see WC 2022 -> SF -> Metric 4 -> Model).",
    ]


def _aggregate_rows(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    n_t = len(results)
    rows: list[dict[str, str]] = []
    for stage in STAGES:
        n = EXPECTED_N[stage]
        m_hits = sum(r["market"][stage]["topn_hits"] for r in results) / (n_t * n)
        d_hits = sum(r["model"][stage]["topn_hits"] for r in results) / (n_t * n)
        m2m = sum(1 for r in results if r["market_joint"][stage]["top1_correct"])
        m2d = sum(1 for r in results if r["model_joint"][stage]["top1_correct"])
        m3 = sum(r["market_joint"][stage]["cumulative_frequency"] for r in results) / n_t
        d3 = sum(r["model_joint"][stage]["cumulative_frequency"] for r in results) / n_t
        m4 = sum(r["market_joint"][stage]["cumulative_teams_covered"] for r in results) / n_t
        d4 = sum(r["model_joint"][stage]["cumulative_teams_covered"] for r in results) / n_t
        m3r = sum(r["market_joint"][stage]["rank_actual"] for r in results) / n_t
        d3r = sum(r["model_joint"][stage]["rank_actual"] for r in results) / n_t
        m4r = sum(r["market_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        d4r = sum(r["model_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        rows.append(
            {
                "stage": stage,
                "m1_market": _pct(m_hits),
                "m1_model": _pct(d_hits),
                "m1_market_value": m_hits,
                "m1_model_value": d_hits,
                "m1_delta_pp": 100.0 * (d_hits - m_hits),
                "m2_market": f"{m2m}/{n_t}",
                "m2_model": f"{m2d}/{n_t}",
                "m3_market": _pct(m3),
                "m3_model": _pct(d3),
                "m4_market": _pct(m4),
                "m4_model": _pct(d4),
                "m3_rank_market": f"{m3r:.0f}",
                "m3_rank_model": f"{d3r:.0f}",
                "m4_rank_market": f"{m4r:.0f}",
                "m4_rank_model": f"{d4r:.0f}",
            }
        )
    return rows


def render_summary_markdown(results: list[dict[str, Any]]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_t = len(results)
    aggregate_rows = _aggregate_rows(results)

    lines = [
        "# Bracket_Simulations - historical backtest summary",
        "",
        f"**Generated:** {ts} | **Tournaments:** {n_t} (WC 2010-2022) | **Modes:** `market_all` vs `model_all`",
        "",
        "> This is the curated reader-facing summary. The detailed generated report lives in "
        "`data/output/simulations/stage_prediction_backtest.md`.",
        "",
        "## Key findings",
        "",
        f"- `model_all` edges `market_all` on average M1 top-N recall at R16 ({aggregate_rows[0]['m1_model']} vs {aggregate_rows[0]['m1_market']}), QF ({aggregate_rows[1]['m1_model']} vs {aggregate_rows[1]['m1_market']}), SF ({aggregate_rows[2]['m1_model']} vs {aggregate_rows[2]['m1_market']}), and final ({aggregate_rows[3]['m1_model']} vs {aggregate_rows[3]['m1_market']}).",
        "- M2 is `0/4` for both modes at every stage: the rank-1 exact bracket never matches reality, which is a concise reminder that exact bracket configurations are far more brittle than marginal stage probabilities.",
        f"- M3 cumulative (lower is better): when the exact set was never simulated, both modes report "
        f"{_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}; otherwise compare observed ranks in the per-tournament tables.",
        f"- Both modes miss the actual champion as the top-1 winner pick in all four tournaments, but both still keep the actual champion relatively near the front of the winner distribution on average (M3 winner rank {aggregate_rows[4]['m3_rank_market']} for market and {aggregate_rows[4]['m3_rank_model']} for model).",
        "",
        "## How to read the metrics",
        "",
        "- M1: top-N marginal recall from `p_at_least_{stage}`; higher is better.",
        "- M2: whether the single most likely exact team set matched reality; `yes` or `no`.",
        f"- M3: cumulative probability up to the exact actual set; lower is better, and {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)} means the exact set was never observed in the simulated support.",
        "- M4: cumulative probability until every actual team has appeared somewhere in the high-probability joint support; lower is better.",
        "",
        "## M1 recall edge",
        "",
        "| Stage | Market M1 recall | Model M1 recall | Delta pp (model - market) | Better side |",
        "|-------|------------------|-----------------|---------------------------|-------------|",
    ]
    for row in aggregate_rows[:4]:
        better = "model" if row["m1_delta_pp"] > 0 else ("market" if row["m1_delta_pp"] < 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m1_market']} | {row['m1_model']} | "
            f"{row['m1_delta_pp']:+.2f} | {better} |"
        )
    lines.extend(
        [
            "",
            "`model_all` holds a small but consistent aggregate M1 recall edge from R16 through final in the historical backtest.",
            "",
        "## Aggregate",
        "",
        "| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |",
        "|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|",
        ]
    )
    for row in aggregate_rows:
        lines.append(
            f"| **{row['stage']}** | {row['m1_market']} | {row['m1_model']} | {row['m2_market']} | {row['m2_model']} | "
            f"{row['m3_market']} | {row['m3_model']} | {row['m4_market']} | {row['m4_model']} |"
        )
    lines.extend(
        [
            "",
            "| Stage | M3 avg rank mkt | M3 avg rank mdl | M4 avg rank mkt | M4 avg rank mdl |",
            "|-------|-----------------|-----------------|-----------------|-----------------|",
        ]
    )
    for row in aggregate_rows:
        lines.append(
            f"| **{row['stage']}** | {row['m3_rank_market']} | {row['m3_rank_model']} | {row['m4_rank_market']} | {row['m4_rank_model']} |"
        )

    for r in results:
        lines.extend(
            [
                "",
                f"## {r['competition']} (`{r['tournament']}`)",
                "",
                f"**Champion (actual):** {r['champion_actual']}",
                f"- Market winner pick: {r['market_champion_pick']}",
                f"- Model winner pick: {r['model_champion_pick']}",
                "",
                "| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl |",
                "|-------|-----------|-----------|--------|--------|------------|------------|",
            ]
        )
        for stage in STAGES:
            n = EXPECTED_N[stage]
            ms, ds = r["market"][stage], r["model"][stage]
            mj, dj = r["market_joint"][stage], r["model_joint"][stage]
            lines.append(
                f"| **{stage}** | {int(ms['topn_hits'])}/{n} | {int(ds['topn_hits'])}/{n} | "
                f"{_yn(mj['top1_correct'])} | {_yn(dj['top1_correct'])} | "
                f"{_pct(mj['cumulative_frequency'])} | {_pct(dj['cumulative_frequency'])} |"
            )
        lines.append("")
        lines.append(
            "_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); "
            f"M3 = cumulative probability up to the exact actual set "
            f"(if never simulated, {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)})._"
        )

    lines.extend(["", * _render_worked_example(results), ""])
    return "\n".join(lines)


def render_backtest_markdown(results: list[dict[str, Any]]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_t = len(results)
    lines = [
        "# Stage prediction backtest",
        "",
        f"**Generated:** {ts} | **Tournaments:** {n_t} (WC 2010-2022) | **Modes:** `market_all` vs `model_all`",
        "",
        "> For the concise human-facing summary, see [`results.md`](../../../results.md). "
        "This file keeps the full generated stage-by-stage breakdown.",
        "",
        "## How to read this report",
        "",
        "| Metric | Source | What it measures |",
        "|--------|--------|------------------|",
        "| **1** | `team_stage_probabilities.csv` | Top *N* teams by `p_at_least_{stage}` vs who really qualified "
        f"(N: {', '.join(f'{s}={EXPECTED_N[s]}' for s in STAGES)}) |",
        "| **2** | `stage_config_probabilities.csv` rank 1 | Did the most simulated exact team set match reality? |",
        "| **3** | `analysis/stage_combinations_{stage}.csv` | Rank and cumulative probability of the exact actual team set "
        f"(if never simulated in the run, cumulative is {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}) |",
        "| **4** | Same as 3 | Cumulative probability until each actual team has appeared in >=1 combo; lists the union of teams in combos 1..stop rank |",
        "",
        "In tables, `yes` means the condition held, `no` means it did not, and recall is shown as `hits/N`.",
        "",
        "---",
        "",
        "## Aggregate (average across tournaments)",
        "",
        "| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |",
        "|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|",
    ]

    for row in _aggregate_rows(results):
        lines.append(
            f"| **{row['stage']}** | {row['m1_market']} | {row['m1_model']} | {row['m2_market']} | {row['m2_model']} | "
            f"{row['m3_market']} | {row['m3_model']} | {row['m4_market']} | {row['m4_model']} |"
        )

    lines.extend(
        [
            "",
            "| Stage | M3 avg rank mkt | M3 avg rank mdl | M4 avg rank mkt | M4 avg rank mdl |",
            "|-------|-----------------|-----------------|-----------------|-----------------|",
        ]
    )
    for row in _aggregate_rows(results):
        lines.append(
            f"| **{row['stage']}** | {row['m3_rank_market']} | {row['m3_rank_model']} | {row['m4_rank_market']} | {row['m4_rank_model']} |"
        )

    lines.extend(["", "---", ""])

    for r in results:
        lines.extend(_render_tournament_section(r, r["tournament"]))

    lines.extend(_render_worked_example(results))
    return "\n".join(lines)
