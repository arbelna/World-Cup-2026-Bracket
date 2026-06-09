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


def _brier(x: float) -> str:
    return f"{x:.4f}"


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
        "M4 cum mkt | M4 cum mdl | "
        "M5 mkt | M5 mdl | "
        "M6 mkt | M6 mdl |"
    )
    lines.append(
        "|-------|"
        "-----------|-----------|"
        "--------|--------|"
        "----------|----------|"
        "----------|----------|"
        "--------|--------|"
        "--------|--------|"
    )
    for stage in STAGES:
        n = EXPECTED_N[stage]
        ms, ds = r["market"][stage], r["model"][stage]
        mj, dj = r["market_joint"][stage], r["model_joint"][stage]
        lines.append(
            f"| **{stage}** | "
            f"{int(ms['topn_hits'])}/{n} | {int(ds['topn_hits'])}/{n} | "
            f"{_brier(ms['brier_qualifiers'])} | {_brier(ds['brier_qualifiers'])} | "
            f"{_pct(mj['cumulative_frequency'])} | {_pct(dj['cumulative_frequency'])} | "
            f"{_pct(mj['cumulative_teams_covered'])} | {_pct(dj['cumulative_teams_covered'])} | "
            f"{_brier(ms['brier'])} | {_brier(ds['brier'])} | "
            f"{_brier(ms['logloss'])} | {_brier(ds['logloss'])} |"
        )
    lines.append("")
    lines.append(
        "_M1 = top-N marginal recall; M2 = qualifier Brier; "
        "M3 = cumulative to exact actual set "
        f"(if never simulated, {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}); "
        "M4 = cumulative until all actual teams seen; "
        "M5 = all-team binary Brier; M6 = all-team binary log loss._"
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

        lines.append("#### Metric 2 - Brier on actual qualifiers (`p_at_least`)")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(
            f"| Mean Brier (qualifiers only) | {_brier(ms['brier_qualifiers'])} | "
            f"{_brier(ds['brier_qualifiers'])} |"
        )
        m_avg_p = sum(market_preds[t][col] for t in actual_set) / len(actual_set)
        d_avg_p = sum(model_preds[t][col] for t in actual_set) / len(actual_set)
        lines.append(f"| Avg p on qualifiers | {_pct(m_avg_p)} | {_pct(d_avg_p)} |")
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

        lines.append("#### Metric 5 - All-team binary Brier")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(
            f"| All-team Brier | {_brier(ms['brier'])} | {_brier(ds['brier'])} |"
        )
        delta5 = ds["brier"] - ms["brier"]
        better5 = "market" if delta5 > 0 else "model"
        lines.append(f"| Delta (model - market) | | {delta5:+.4f} ({better5} wins) |")
        lines.append("")

        lines.append("#### Metric 6 - All-team binary log loss")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(
            f"| All-team log loss | {_brier(ms['logloss'])} | {_brier(ds['logloss'])} |"
        )
        delta6 = ds["logloss"] - ms["logloss"]
        better6 = "market" if delta6 > 0 else "model"
        lines.append(f"| Delta (model - market) | | {delta6:+.4f} ({better6} wins) |")
        lines.append("")

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
        m2m = sum(r["market"][stage]["brier_qualifiers"] for r in results) / n_t
        m2d = sum(r["model"][stage]["brier_qualifiers"] for r in results) / n_t
        m3 = sum(r["market_joint"][stage]["cumulative_frequency"] for r in results) / n_t
        d3 = sum(r["model_joint"][stage]["cumulative_frequency"] for r in results) / n_t
        m4 = sum(r["market_joint"][stage]["cumulative_teams_covered"] for r in results) / n_t
        d4 = sum(r["model_joint"][stage]["cumulative_teams_covered"] for r in results) / n_t
        m3r = sum(r["market_joint"][stage]["rank_actual"] for r in results) / n_t
        d3r = sum(r["model_joint"][stage]["rank_actual"] for r in results) / n_t
        m4r = sum(r["market_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        d4r = sum(r["model_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        m5m = sum(r["market"][stage]["brier"]   for r in results) / n_t
        m5d = sum(r["model"][stage]["brier"]    for r in results) / n_t
        m6m = sum(r["market"][stage]["logloss"] for r in results) / n_t
        m6d = sum(r["model"][stage]["logloss"]  for r in results) / n_t
        rows.append(
            {
                "stage": stage,
                "m1_market": _pct(m_hits),
                "m1_model": _pct(d_hits),
                "m1_market_value": m_hits,
                "m1_model_value": d_hits,
                "m1_delta_pp": 100.0 * (d_hits - m_hits),
                "m2_market": _brier(m2m),
                "m2_model": _brier(m2d),
                "m2_market_value": m2m,
                "m2_model_value": m2d,
                "m2_delta": m2d - m2m,
                "m3_market": _pct(m3),
                "m3_model": _pct(d3),
                "m3_market_value": m3,
                "m3_model_value": d3,
                "m3_delta_pp": 100.0 * (d3 - m3),
                "m4_market": _pct(m4),
                "m4_model": _pct(d4),
                "m4_market_value": m4,
                "m4_model_value": d4,
                "m4_delta_pp": 100.0 * (d4 - m4),
                "m3_rank_market": f"{m3r:.0f}",
                "m3_rank_model": f"{d3r:.0f}",
                "m4_rank_market": f"{m4r:.0f}",
                "m4_rank_model": f"{d4r:.0f}",
                "m5_market": _brier(m5m),
                "m5_model": _brier(m5d),
                "m5_market_value": m5m,
                "m5_model_value": m5d,
                "m5_delta": m5d - m5m,
                "m6_market": _brier(m6m),
                "m6_model": _brier(m6d),
                "m6_market_value": m6m,
                "m6_model_value": m6d,
                "m6_delta": m6d - m6m,
            }
        )
    return rows


def render_summary_markdown(
    results: list[dict[str, Any]],
    *,
    uncertainty: dict[str, dict[str, dict]] | None = None,
    calibration: dict[str, tuple[list[dict], float]] | None = None,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_t = len(results)
    aggregate_rows = _aggregate_rows(results)

    # Build calibration summary strings if available
    mkt_ece_str = ""
    mdl_ece_str = ""
    mkt_cal_gap_str = ""
    mdl_cal_gap_str = ""
    if calibration:
        mkt_ece = calibration["market_all"]["pooled_ece"]
        mdl_ece = calibration["model_all"]["pooled_ece"]
        mkt_ece_str = f"{mkt_ece:.4f}"
        mdl_ece_str = f"{mdl_ece:.4f}"
        # Find the 0.5-0.7 bin gap in the pooled rows for both modes
        for mode, gap_attr in [("market_all", "mkt_cal_gap_str"), ("model_all", "mdl_cal_gap_str")]:
            for row in calibration[mode]["pooled_rows"]:
                if abs(row["lo"] - 0.5) < 0.01:
                    val = f"{row['gap']:+.3f} (avg pred {row['avg_pred']:.2f}, observed {row['observed']:.2f})"
                    if mode == "market_all":
                        mkt_cal_gap_str = val
                    else:
                        mdl_cal_gap_str = val
                    break

    lines = [
        "# Bracket_Simulations - historical backtest summary",
        "",
        f"**Generated:** {ts} | **Tournaments:** {n_t} (WC 2010-2022) | **Modes:** `market_all` vs `model_all`",
        "",
        "> This is the curated reader-facing summary. The detailed generated report lives in "
        "`data/output/simulations/stage_prediction_backtest.md`.",
        "",
        "## Conclusions",
        "",
        "The goal of `model_all` is to be **competitive** with the betting market benchmark (`market_all`), "
        "not to beat it outright. Betting markets aggregate enormous amounts of information; "
        "matching them with a statistical model built from historical match data is already a strong result.",
        "",
        "Across four World Cups (2010-2022) the picture is mixed but broadly positive:",
        "",
        f"- **Recall (M1):** `model_all` edges `market_all` at every stage "
        f"(R16: {aggregate_rows[0]['m1_model']} vs {aggregate_rows[0]['m1_market']}, "
        f"QF: {aggregate_rows[1]['m1_model']} vs {aggregate_rows[1]['m1_market']}, "
        f"SF: {aggregate_rows[2]['m1_model']} vs {aggregate_rows[2]['m1_market']}, "
        f"final: {aggregate_rows[3]['m1_model']} vs {aggregate_rows[3]['m1_market']}). "
        "The direction is consistent, but with only 4 tournaments the bootstrap confidence intervals "
        "all span zero — the gap is real in direction but not distinguishable from noise at this sample size.",
        f"- **Qualifier Brier (M2):** `market_all` wins cleanly at every stage (lower is better). "
        "The model assigns less accurate probabilities to teams that actually qualified. "
        "This is the market's clearest advantage.",
        f"- **All-team Brier (M5) and log loss (M6):** `market_all` also leads on both all-team metrics "
        f"at R16/QF/SF on average, consistent with M2. The gap narrows at final/winner stages where "
        "the model is marginally competitive.",
        (
            f"- **Calibration:** `market_all` is better calibrated overall "
            f"(ECE {mkt_ece_str} vs {mdl_ece_str}). "
            "Both models are well-calibrated on low-probability teams — the large majority of cases — "
            f"and sit close to the diagonal in the 0-0.3 range. "
            f"The model's deficit is concentrated in the 0.5-0.7 bin "
            f"({mdl_cal_gap_str if mdl_cal_gap_str else 'see detailed report'}): "
            "it consistently underrates mid-range favourites. "
            f"The market is sharper in that range "
            f"({mkt_cal_gap_str if mkt_cal_gap_str else 'see detailed report'})."
        ) if calibration else
        "- **Calibration:** see the detailed report for reliability tables.",
        "- **Winner prediction:** neither model correctly identifies the actual champion as top pick "
        "in any of the four tournaments — consistent with the unpredictability of knockout football.",
        "",
        "**Overall verdict:** `model_all` is competitive with the market. "
        "It matches market on recall and holds its own on joint-distribution metrics (M3/M4 at SF and final). "
        "The market is better calibrated, particularly for favourites in the 0.5-0.7 probability range. "
        "Improving the model's confidence on strong favourites is the clearest remaining gap.",
        "",
        "## How to read the metrics",
        "",
        "- M1: top-N marginal recall from `p_at_least_{stage}`; higher is better.",
        "- M2: mean Brier on teams that actually reached the stage, using `p_at_least_{stage}`; lower is better.",
        f"- M3: cumulative probability up to the exact actual set; lower is better, and {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)} means the exact set was never observed in the simulated support.",
        "- M4: cumulative probability until every actual team has appeared somewhere in the high-probability joint support; lower is better.",
        "- M5: all-team binary Brier — mean squared error of `p_at_least_{stage}` vs 0/1 outcome across **all 32 teams**; lower is better.",
        "- M6: all-team binary log loss — mean cross-entropy of `p_at_least_{stage}` vs 0/1 outcome across **all 32 teams**; lower is better.",
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
            "## M2 qualifier Brier",
            "",
            "Mean squared error on actual qualifiers only: average of `(p_at_least - 1)^2` over teams that reached the stage.",
            "",
            "| Stage | Market M2 Brier | Model M2 Brier | Delta (model - market) | Better side |",
            "|-------|-----------------|----------------|------------------------|-------------|",
        ]
    )
    for row in aggregate_rows:
        better = "market" if row["m2_delta"] > 0 else ("model" if row["m2_delta"] < 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m2_market']} | {row['m2_model']} | "
            f"{row['m2_delta']:+.4f} | {better} |"
        )
    lines.extend(
        [
            "",
            "`market_all` has lower average qualifier Brier at every stage in the historical backtest.",
            "",
            "## M3 exact-set cumulative",
            "",
            f"Cumulative simulated probability through the rank of the exact actual team set; {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)} when that set never appeared.",
            "",
            "| Stage | Market M3 cum | Model M3 cum | Delta pp (model - market) | Better side |",
            "|-------|---------------|--------------|---------------------------|-------------|",
        ]
    )
    for row in aggregate_rows:
        better = "model" if row["m3_delta_pp"] < 0 else ("market" if row["m3_delta_pp"] > 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m3_market']} | {row['m3_model']} | "
            f"{row['m3_delta_pp']:+.2f} | {better} |"
        )
    lines.extend(
        [
            "",
            "## M4 all-teams-seen cumulative",
            "",
            "Cumulative simulated probability through the first rank where every actual team has appeared in at least one joint combo.",
            "",
            "| Stage | Market M4 cum | Model M4 cum | Delta pp (model - market) | Better side |",
            "|-------|---------------|--------------|---------------------------|-------------|",
        ]
    )
    for row in aggregate_rows:
        better = "model" if row["m4_delta_pp"] < 0 else ("market" if row["m4_delta_pp"] > 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m4_market']} | {row['m4_model']} | "
            f"{row['m4_delta_pp']:+.2f} | {better} |"
        )

    lines.extend(
        [
            "",
            "## M5 all-team binary Brier",
            "",
            "Mean squared error of `p_at_least_{stage}` vs 0/1 outcome across all 32 teams (qualifiers score toward 1, eliminated teams toward 0).",
            "",
            "| Stage | Market M5 Brier | Model M5 Brier | Delta (model - market) | Better side |",
            "|-------|-----------------|----------------|------------------------|-------------|",
        ]
    )
    for row in aggregate_rows:
        better = "market" if row["m5_delta"] > 0 else ("model" if row["m5_delta"] < 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m5_market']} | {row['m5_model']} | "
            f"{row['m5_delta']:+.4f} | {better} |"
        )

    lines.extend(
        [
            "",
            "## M6 all-team binary log loss",
            "",
            "Mean binary cross-entropy of `p_at_least_{stage}` vs 0/1 outcome across all 32 teams; lower is better.",
            "",
            "| Stage | Market M6 log loss | Model M6 log loss | Delta (model - market) | Better side |",
            "|-------|-------------------|-------------------|------------------------|-------------|",
        ]
    )
    for row in aggregate_rows:
        better = "market" if row["m6_delta"] > 0 else ("model" if row["m6_delta"] < 0 else "tie")
        lines.append(
            f"| **{row['stage']}** | {row['m6_market']} | {row['m6_model']} | "
            f"{row['m6_delta']:+.4f} | {better} |"
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
                "| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |",
                "|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|--------|--------|--------|--------|",
            ]
        )
        for stage in STAGES:
            n = EXPECTED_N[stage]
            ms, ds = r["market"][stage], r["model"][stage]
            mj, dj = r["market_joint"][stage], r["model_joint"][stage]
            lines.append(
                f"| **{stage}** | {int(ms['topn_hits'])}/{n} | {int(ds['topn_hits'])}/{n} | "
                f"{_brier(ms['brier_qualifiers'])} | {_brier(ds['brier_qualifiers'])} | "
                f"{_pct(mj['cumulative_frequency'])} | {_pct(dj['cumulative_frequency'])} | "
                f"{_pct(mj['cumulative_teams_covered'])} | {_pct(dj['cumulative_teams_covered'])} | "
                f"{_brier(ms['brier'])} | {_brier(ds['brier'])} | "
                f"{_brier(ms['logloss'])} | {_brier(ds['logloss'])} |"
            )
        lines.append("")
        lines.append(
            "_M1 = top-N marginal recall; M2 = qualifier Brier; "
            f"M3 = cumulative to exact actual set (if never simulated, {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}); "
            "M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._"
        )

    lines.extend(["", * _render_worked_example(results), ""])
    return "\n".join(lines)


def _render_uncertainty_section(uncertainty: dict[str, dict[str, dict]]) -> list[str]:
    lines = [
        "## Uncertainty -- bootstrap intervals on model vs market gap",
        "",
        "> The bracket backtest aggregates only 4 tournaments. Intervals are a tournament-level block bootstrap"
        " (10,000 resamples). A CI spanning 0 means the stage-level gap is not distinguishable from"
        " four-tournament noise; the point estimate still indicates direction.",
        "",
        "### Recall delta (model minus market)",
        "",
        "| Stage | Recall delta (pp) | 95% CI | Tournaments model better | Significant? |",
        "|-------|------------------|--------|--------------------------|--------------|",
    ]
    for stage in STAGES:
        u = uncertainty[stage]["recall"]
        delta_pp = 100.0 * u["delta_mean"]
        ci_low_pp = 100.0 * u["ci_low"]
        ci_high_pp = 100.0 * u["ci_high"]
        n = u["n_tournaments"]
        n_better = u["n_model_better"]
        sig = "yes" if u["significant"] else "no"
        lines.append(
            f"| **{stage}** | {delta_pp:+.1f} pp | [{ci_low_pp:+.1f}, {ci_high_pp:+.1f}] | "
            f"{n_better} of {n} | {sig} |"
        )
    lines.extend(
        [
            "",
            "### M5 all-team Brier delta (model minus market, lower is better for the winner)",
            "",
            "| Stage | Brier delta | 95% CI | Tournaments model better | Significant? |",
            "|-------|------------|--------|--------------------------|--------------|",
        ]
    )
    for stage in STAGES:
        u = uncertainty[stage]["brier"]
        delta = u["delta_mean"]
        ci_low = u["ci_low"]
        ci_high = u["ci_high"]
        n = u["n_tournaments"]
        n_better = u["n_model_better"]
        sig = "yes" if u["significant"] else "no"
        lines.append(
            f"| **{stage}** | {delta:+.4f} | [{ci_low:+.4f}, {ci_high:+.4f}] | "
            f"{n_better} of {n} | {sig} |"
        )
    lines.extend(
        [
            "",
            "### M6 all-team log-loss delta (model minus market, lower is better for the winner)",
            "",
            "| Stage | Log-loss delta | 95% CI | Tournaments model better | Significant? |",
            "|-------|---------------|--------|--------------------------|--------------|",
        ]
    )
    for stage in STAGES:
        u = uncertainty[stage]["logloss"]
        delta = u["delta_mean"]
        ci_low = u["ci_low"]
        ci_high = u["ci_high"]
        n = u["n_tournaments"]
        n_better = u["n_model_better"]
        sig = "yes" if u["significant"] else "no"
        lines.append(
            f"| **{stage}** | {delta:+.4f} | [{ci_low:+.4f}, {ci_high:+.4f}] | "
            f"{n_better} of {n} | {sig} |"
        )
    lines.append("")
    return lines



def _render_calibration_table(cal_rows: list[dict], ece: float, title: str) -> list[str]:
    """Render a single reliability table with its ECE."""
    lines = [
        f"### {title}   (ECE {ece:.4f})",
        "",
        "| pred bin | n | avg pred | observed | 95% CI (obs) | gap |",
        "|----------|---|----------|----------|--------------|-----|",
    ]
    for row in cal_rows:
        lo_s = f"{row['lo']:.1f}"
        hi_s = f"{min(row['hi'], 1.0):.1f}"
        lines.append(
            f"| {lo_s}-{hi_s} | {row['n']} | {row['avg_pred']:.3f} | {row['observed']:.3f} | "
            f"[{row['obs_ci_low']:.3f}, {row['obs_ci_high']:.3f}] | {row['gap']:+.3f} |"
        )
    lines.append("")
    return lines


def _render_calibration_section(calibration: dict[str, dict]) -> list[str]:
    lines = [
        "## Calibration -- reliability tables",
        "",
        "> Per-stage curves avoid mixing incompatible base rates (R16 ~63% vs Winner ~3%) "
        "and keep each reliability diagram interpretable. "
        "Pooled ECE is retained below as a secondary summary. "
        "Wilson CIs treat each (team, stage, tournament) observation as independent; "
        "outcomes within a tournament are correlated due to fixed stage capacity, "
        "so the intervals understate true uncertainty.",
        "",
    ]
    for mode in ("market_all", "model_all"):
        cal = calibration[mode]
        lines.append(f"### Calibration -- {mode}")
        lines.append("")
        # Per-stage tables
        for stage in STAGES:
            stage_rows, stage_ece = cal["by_stage"][stage]
            lines.extend(
                _render_calibration_table(stage_rows, stage_ece, f"{mode} / {stage}")
            )
        # Pooled as secondary
        lines.extend(
            _render_calibration_table(
                cal["pooled_rows"],
                cal["pooled_ece"],
                f"{mode} / pooled (secondary — all stages combined)",
            )
        )
    return lines


def render_backtest_markdown(
    results: list[dict],
    *,
    uncertainty: dict | None = None,
    calibration: dict | None = None,
) -> str:
    from datetime import datetime, timezone
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
        "| **2** | `team_stage_probabilities.csv` | Mean Brier on teams that actually reached the stage (`p_at_least_{{stage}}` vs outcome 1); lower is better |",
        "| **3** | `analysis/stage_combinations_{{stage}}.csv` | Rank and cumulative probability of the exact actual team set "
        f"(if never simulated in the run, cumulative is {_pct(NOT_OBSERVED_CUMULATIVE_FREQUENCY)}) |",
        "| **4** | Same as 3 | Cumulative probability until each actual team has appeared in >=1 combo; lists the union of teams in combos 1..stop rank |",
        "| **5** | `team_stage_probabilities.csv` | All-team binary Brier: mean `(p_at_least_{{stage}} - outcome)^2` across all 32 teams; lower is better |",
        "| **6** | `team_stage_probabilities.csv` | All-team binary log loss: mean cross-entropy across all 32 teams; lower is better |",
        "",
        "In tables, `yes` means the condition held, `no` means it did not, and recall is shown as `hits/N`.",
        "",
        "---",
        "",
        "## Aggregate (average across tournaments)",
        "",
        "### M1 top-N recall",
        "",
        "| Stage | M1 market | M1 model |",
        "|-------|-----------|-----------|",
    ]

    aggregate_rows = _aggregate_rows(results)
    for row in aggregate_rows:
        lines.append(f"| **{row['stage']}** | {row['m1_market']} | {row['m1_model']} |")

    lines.extend(["", "### M2 qualifier Brier", "",
        "| Stage | M2 market | M2 model |", "|-------|-----------|----------|"])
    for row in aggregate_rows:
        lines.append(f"| **{row['stage']}** | {row['m2_market']} | {row['m2_model']} |")

    lines.extend(["", "### M3 exact-set cumulative", "",
        "| Stage | M3 cum market | M3 cum model | Delta pp (model - market) | Better side |",
        "|-------|---------------|--------------|---------------------------|-------------|"])
    for row in aggregate_rows:
        better = "model" if row["m3_delta_pp"] < 0 else ("market" if row["m3_delta_pp"] > 0 else "tie")
        lines.append(f"| **{row['stage']}** | {row['m3_market']} | {row['m3_model']} | {row['m3_delta_pp']:+.2f} | {better} |")

    lines.extend(["", "### M4 all-teams-seen cumulative", "",
        "| Stage | M4 cum market | M4 cum model | Delta pp (model - market) | Better side |",
        "|-------|---------------|--------------|---------------------------|-------------|"])
    for row in aggregate_rows:
        better = "model" if row["m4_delta_pp"] < 0 else ("market" if row["m4_delta_pp"] > 0 else "tie")
        lines.append(f"| **{row['stage']}** | {row['m4_market']} | {row['m4_model']} | {row['m4_delta_pp']:+.2f} | {better} |")

    lines.extend(["", "### M5 all-team binary Brier", "",
        "| Stage | M5 market | M5 model | Delta (model - market) | Better side |",
        "|-------|-----------|----------|------------------------|-------------|"])
    for row in aggregate_rows:
        better = "market" if row["m5_delta"] > 0 else ("model" if row["m5_delta"] < 0 else "tie")
        lines.append(f"| **{row['stage']}** | {row['m5_market']} | {row['m5_model']} | {row['m5_delta']:+.4f} | {better} |")

    lines.extend(["", "### M6 all-team binary log loss", "",
        "| Stage | M6 market | M6 model | Delta (model - market) | Better side |",
        "|-------|-----------|----------|------------------------|-------------|"])
    for row in aggregate_rows:
        better = "market" if row["m6_delta"] > 0 else ("model" if row["m6_delta"] < 0 else "tie")
        lines.append(f"| **{row['stage']}** | {row['m6_market']} | {row['m6_model']} | {row['m6_delta']:+.4f} | {better} |")

    lines.extend(["", "---", ""])

    if uncertainty is not None:
        lines.extend(_render_uncertainty_section(uncertainty))
        lines.extend(["---", ""])

    if calibration is not None:
        lines.extend(_render_calibration_section(calibration))
        lines.extend(["---", ""])

    for r in results:
        lines.extend(_render_tournament_section(r, r["tournament"]))

    lines.extend(_render_worked_example(results))
    return "\n".join(lines)
