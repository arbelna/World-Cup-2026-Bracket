"""Stage prediction backtest reports (market_all vs model_all)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bracket_simulations.actual_results import EXPECTED_N, STAGES, build_actual_outcome
from bracket_simulations.aggregates import (
    load_state,
    resolve_bracket_output_dir,
    settings_fingerprint,
    top_config_for_stage,
)
from bracket_simulations.analysis import analyze_bracket_dir, combos_for_stage, cumulative_coverage
from bracket_simulations.compare import (
    _load_preds,
    evaluate_joint,
    evaluate_marginal,
    probabilities_csv,
    state_json,
)
from bracket_simulations.config import load_tournament_config
from bracket_simulations.paths import DATA_OUTPUT, STAGE_ROOT
from bracket_simulations.prediction_backtest_report import (
    NOT_OBSERVED_CUMULATIVE_FREQUENCY,
    render_backtest_markdown,
    render_summary_markdown,
)
from bracket_simulations.simulator.bracket_resolver import load_groups

HISTORICAL_TOURNAMENTS = ["wc2010", "wc2014", "wc2018", "wc2022"]
MODES = ("market_all", "model_all")


def _cumulative_until_all_teams_seen(
    state: dict, stage: str, actual: tuple[str, ...]
) -> dict[str, float | int | str | list[str]]:
    total = int(state.get("total_sims", 0))
    if total <= 0:
        return {
            "rank_teams_covered": 0,
            "cumulative_teams_covered": 0.0,
            "last_team_covered": "",
            "combo_at_coverage": "",
            "teams_in_predictions": [],
            "teams_in_predictions_n": 0,
            "teams_actual_in_union": [],
            "teams_extras_in_union": [],
        }
    target = set(actual)
    combos = combos_for_stage(state, stage)
    first_seen: dict[str, int] = {}
    covered: set[str] = set()
    combo_at = ""
    for i, (teams, count) in enumerate(combos):
        rank = i + 1
        before = set(covered)
        covered.update(teams)
        for t in teams:
            if t in target and t not in before and t not in first_seen:
                first_seen[t] = rank
        combo_at = "|".join(teams)
        if target <= covered:
            break
    if target <= covered:
        last_team = max(first_seen, key=first_seen.get)
        stop_rank = first_seen[last_team]
        cum_stop = sum(combos[j][1] for j in range(stop_rank)) / total
        combo_at = "|".join(combos[stop_rank - 1][0])
        union_teams: set[str] = set()
        for j in range(stop_rank):
            union_teams.update(combos[j][0])
        teams_list = sorted(union_teams)
        return {
            "rank_teams_covered": stop_rank,
            "cumulative_teams_covered": cum_stop,
            "last_team_covered": last_team,
            "combo_at_coverage": combo_at,
            "teams_in_predictions": teams_list,
            "teams_in_predictions_n": len(teams_list),
            "teams_actual_in_union": sorted(target & union_teams),
            "teams_extras_in_union": sorted(union_teams - target),
        }
    union_teams: set[str] = set()
    for teams, _ in combos:
        union_teams.update(teams)
    teams_list = sorted(union_teams)
    return {
        "rank_teams_covered": len(combos) + 1,
        "cumulative_teams_covered": 1.0,
        "last_team_covered": "",
        "combo_at_coverage": "",
        "teams_in_predictions": teams_list,
        "teams_in_predictions_n": len(teams_list),
        "teams_actual_in_union": sorted(target & union_teams),
        "teams_extras_in_union": sorted(union_teams - target),
    }


def _cumulative_at_actual(state: dict, stage: str, actual: tuple[str, ...]) -> dict[str, float | int]:
    total = int(state.get("total_sims", 0))
    combos = combos_for_stage(state, stage)
    actual_sorted = tuple(sorted(actual))
    cov = cumulative_coverage(combos, total)
    rank = 0
    p_actual = 0.0
    cum = 0.0
    for i, (teams, _) in enumerate(combos):
        if teams == actual_sorted:
            rank = i + 1
            p_actual, cum = cov[i][1], cov[i][2]
            break
    if rank == 0:
        rank = len(combos) + 1
        cum = NOT_OBSERVED_CUMULATIVE_FREQUENCY
    return {
        "rank_actual": rank,
        "p_joint_actual": p_actual,
        "cumulative_frequency": cum,
        "n_unique_configs": len(combos),
        "joint_actual_observed": rank <= len(combos),
    }


def _enrich_joint(state: dict, actual_config: dict[str, tuple[str, ...]]) -> dict[str, dict]:
    base = evaluate_joint(state, actual_config)
    for stage in STAGES:
        actual = tuple(sorted(actual_config[stage]))
        cum = _cumulative_at_actual(state, stage, actual)
        teams_cov = _cumulative_until_all_teams_seen(state, stage, actual)
        top = top_config_for_stage(state, stage)
        base[stage].update(cum)
        base[stage].update(teams_cov)
        if top:
            base[stage]["top1_teams"] = "|".join(top[0])
            base[stage]["top1_probability"] = top[1]
    return base


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _yn(ok: bool) -> str:
    return "✓" if ok else "—"


def _team_rows(teams: list[str], *, per_row: int = 6) -> list[str]:
    if not teams:
        return ["_(none)_"]
    rows: list[str] = []
    for i in range(0, len(teams), per_row):
        rows.append(" · ".join(teams[i : i + per_row]))
    return rows


def _render_team_block(title: str, teams: list[str]) -> list[str]:
    lines = [f"**{title}** — {len(teams)} teams"]
    for row in _team_rows(teams):
        lines.append(f"> {row}")
    return lines


def build_report(tournaments: list[str]) -> tuple[list[dict], str]:
    rows: list[dict] = []
    for tournament in tournaments:
        cfg = load_tournament_config(tournament)
        groups = load_groups(cfg.groups_file)
        all_teams = sorted({t for ts in groups.values() for t in ts})
        actual = build_actual_outcome(tournament)

        market_preds = _load_preds(probabilities_csv(tournament, "market_all"))
        model_preds = _load_preds(probabilities_csv(tournament, "model_all"))
        market_sum = evaluate_marginal(market_preds, all_teams, actual.actual_at_least)
        model_sum = evaluate_marginal(model_preds, all_teams, actual.actual_at_least)

        m_state = load_state(state_json(tournament, "market_all"))
        d_state = load_state(state_json(tournament, "model_all"))
        market_joint = _enrich_joint(m_state, actual.actual_config)
        model_joint = _enrich_joint(d_state, actual.actual_config)

        rows.append(
            {
                "tournament": tournament,
                "competition": cfg.match_dataset_filter_competition,
                "champion_actual": actual.champion,
                "market_champion_pick": max(all_teams, key=lambda t: market_preds[t]["p_at_least_winner"]),
                "model_champion_pick": max(all_teams, key=lambda t: model_preds[t]["p_at_least_winner"]),
                "actual_config": {k: list(v) for k, v in actual.actual_config.items()},
                "market": market_sum,
                "model": model_sum,
                "market_joint": market_joint,
                "model_joint": model_joint,
            }
        )

    md = render_backtest_markdown(rows)
    return rows, md


def _render_metric4_side(label: str, joint: dict) -> list[str]:
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
        f"| Combo at that rank | `{joint.get('combo_at_coverage', '')}` |",
        f"| Union size (teams in ranks 1–{rank}) | {joint.get('teams_in_predictions_n', 0)} |",
        "",
    ]
    lines.extend(_render_team_block("Actual teams covered", actual))
    lines.append("")
    lines.extend(_render_team_block("Other teams in union (not in actual set)", extras))
    lines.append("")
    return lines


def _render_tournament_section(r: dict, tournament_id: str) -> list[str]:
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
        "_M1 = top-N marginal recall · M2 = rank-1 exact set match (✓/—) · "
        "M3 = cumulative to actual set · M4 = cumulative until all actual teams seen in some combo."
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

        lines.append("#### Metric 1 — Top-N by `p_at_least`")
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

        lines.append("#### Metric 2 — Most frequent exact set (rank 1)")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(
            f"| Match actual set | {_yn(mj['top1_correct'])} | {_yn(dj['top1_correct'])} |"
        )
        lines.append(
            f"| Probability | {_pct(mj['top1_probability'])} | {_pct(dj['top1_probability'])} |"
        )
        lines.append(f"| Set | `{mj.get('top1_teams', '')}` | `{dj.get('top1_teams', '')}` |")
        lines.append("")

        actual_pipe = "|".join(actual_sorted)
        lines.append("#### Metric 3 — Exact actual set in joint distribution")
        lines.append("")
        lines.append(f"Target combo: `{actual_pipe}`")
        lines.append("")
        lines.append("| | Market | Model |")
        lines.append("|--|--------|-------|")
        lines.append(
            f"| Rank | {mj['rank_actual']:,} / {mj['n_unique_configs']:,} | "
            f"{dj['rank_actual']:,} / {dj['n_unique_configs']:,} |"
        )
        lines.append(
            f"| p(actual set) | {_pct(mj['p_joint_actual'])} | {_pct(dj['p_joint_actual'])} |"
        )
        lines.append(
            f"| Cumulative through that rank | {_pct(mj['cumulative_frequency'])} | "
            f"{_pct(dj['cumulative_frequency'])} |"
        )
        lines.append("")

        lines.append("#### Metric 4 — All actual teams seen in top combos")
        lines.append("")
        lines.extend(_render_metric4_side("Market", mj))
        lines.extend(_render_metric4_side("Model", dj))

    lines.append("---")
    lines.append("")
    return lines


def _render_markdown(results: list[dict], tournaments: list[str]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_t = len(results)
    lines = [
        "# Stage prediction backtest",
        "",
        f"**Generated:** {ts} · **Tournaments:** {n_t} (WC 2010–2022) · **Modes:** `market_all` vs `model_all`",
        "",
        "## How to read this report",
        "",
        "| Metric | Source | What it measures |",
        "|--------|--------|------------------|",
        "| **1** | `team_stage_probabilities.csv` | Top *N* teams by `p_at_least_{stage}` vs who really qualified "
        f"(N: {', '.join(f'{s}={EXPECTED_N[s]}' for s in STAGES)}) |",
        "| **2** | `stage_config_probabilities.csv` rank 1 | Did the **most simulated** exact team set match reality? |",
        "| **3** | `analysis/stage_combinations_{stage}.csv` | Rank & cumulative probability of the **exact** actual team set |",
        "| **4** | Same as 3 | Rank & cumulative probability when **each** actual team has appeared in "
        "≥1 combo above; lists the **union** of teams in combos 1…stop rank |",
        "",
        "In tables: **✓** = yes / match · **—** = no / miss · Recall shown as `hits/N`.",
        "",
        "---",
        "",
        "## Aggregate (average across tournaments)",
        "",
        "| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |",
        "|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|",
    ]

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
        lines.append(
            f"| **{stage}** | {_pct(m_hits)} | {_pct(d_hits)} | {m2m}/{n_t} | {m2d}/{n_t} | "
            f"{_pct(m3)} | {_pct(d3)} | {_pct(m4)} | {_pct(d4)} |"
        )

    lines.extend(
        [
            "",
            "| Stage | M3 avg rank mkt | M3 avg rank mdl | M4 avg rank mkt | M4 avg rank mdl |",
            "|-------|-----------------|-----------------|-----------------|-----------------|",
        ]
    )
    for stage in STAGES:
        m3r = sum(r["market_joint"][stage]["rank_actual"] for r in results) / n_t
        d3r = sum(r["model_joint"][stage]["rank_actual"] for r in results) / n_t
        m4r = sum(r["market_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        d4r = sum(r["model_joint"][stage]["rank_teams_covered"] for r in results) / n_t
        lines.append(
            f"| **{stage}** | {m3r:.0f} | {d3r:.0f} | {m4r:.0f} | {d4r:.0f} |"
        )

    lines.extend(["", "---", ""])

    for r in results:
        lines.extend(_render_tournament_section(r, r["tournament"]))

    lines.extend(
        [
            "## Worked example — WC 2022 SF (model)",
            "",
            "| | Metric 3 (exact set) | Metric 4 (all teams seen) |",
            "|--|----------------------|---------------------------|",
            "| Target | `Argentina|Croatia|France|Morocco` | Same four teams, any combo |",
            "| Stop rank | 1,068 | **298** |",
            "| Cumulative | 84.38% | **58.92%** |",
            "| Trigger combo | exact quartet | `Argentina|Brazil|France|Morocco` (Morocco last) |",
            "",
            "At rank 298 the model has seen every actual SF team at least once, but only "
            "58.9% of simulated mass — the exact quartet needs rank 1,068 (84.4%).",
            "",
            "Union at rank 298 (**23** teams): all four actual plus 19 others that appeared in "
            "high-frequency SF combos (see WC 2022 → SF → Metric 4 → Model).",
        ]
    )
    return "\n".join(lines)


def write_actual_participants(tournament: str, path: Path | None = None) -> Path:
    cfg = load_tournament_config(tournament)
    actual = build_actual_outcome(tournament)
    out = path or (DATA_OUTPUT / tournament / "actual_participants.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tournament": tournament,
        "competition": cfg.match_dataset_filter_competition,
        "champion": actual.champion,
        "stages": {stage: sorted(actual.actual_config[stage]) for stage in STAGES},
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def write_all_actual_participants(tournaments: list[str] | None = None) -> None:
    for tournament in tournaments or HISTORICAL_TOURNAMENTS:
        path = write_actual_participants(tournament)
        print(f"Wrote {path}")


def analyze_all_outputs(tournaments: list[str] | None = None) -> None:
    for tournament in tournaments or HISTORICAL_TOURNAMENTS:
        cfg = load_tournament_config(tournament)
        for mode in MODES:
            fp = settings_fingerprint(tournament=tournament, mode=mode, alphas=dict(cfg.alphas))
            bracket_dir = resolve_bracket_output_dir(cfg.output_dir, mode=mode, settings_fp=fp)
            if not (bracket_dir / "state.json").exists():
                print(f"SKIP {tournament}/{mode} (no state.json)")
                continue
            print(f"Analyze {tournament}/{mode}/{fp}")
            analyze_bracket_dir(bracket_dir, tournament=tournament)


def write_backtest_reports(tournaments: list[str] | None = None) -> None:
    tlist = tournaments or HISTORICAL_TOURNAMENTS
    data, detailed_md = build_report(tlist)
    summary_path = DATA_OUTPUT / "stage_prediction_backtest.md"
    summary_path.write_text(detailed_md + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}")
    root_results = STAGE_ROOT / "results.md"
    root_results.write_text(render_summary_markdown(data) + "\n", encoding="utf-8")
    print(f"Wrote {root_results}")
    json_path = DATA_OUTPUT / "stage_prediction_backtest.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {json_path}")


def run_historical_sims(
    *,
    n_sims: int = 200_000,
    batch_size: int = 1000,
    seed: int = 42,
    reset: bool = True,
    verbose: bool = True,
    tournaments: list[str] | None = None,
) -> None:
    import argparse

    from bracket_simulations.run import run_simulations

    for tournament in tournaments or HISTORICAL_TOURNAMENTS:
        for mode in MODES:
            print(f"=== Simulate {tournament} {mode} ({n_sims} sims) ===")
            args = argparse.Namespace(
                tournament=tournament,
                mode=mode,
                n_sims=n_sims,
                batch_size=batch_size,
                seed=seed,
                alpha_knockout=None,
                alpha_group_tie=None,
                reset=reset,
                force_reset=False,
                verbose=verbose,
            )
            run_simulations(args)


def run_historical_pipeline(
    *,
    n_sims: int = 200_000,
    batch_size: int = 1000,
    seed: int = 42,
    reset: bool = True,
    skip_sims: bool = False,
    verbose: bool = True,
    tournaments: list[str] | None = None,
) -> None:
    tlist = tournaments or HISTORICAL_TOURNAMENTS
    write_all_actual_participants(tlist)
    if not skip_sims:
        run_historical_sims(
            n_sims=n_sims,
            batch_size=batch_size,
            seed=seed,
            reset=reset,
            verbose=verbose,
            tournaments=tlist,
        )
    analyze_all_outputs(tlist)
    write_backtest_reports(tlist)


def main() -> None:
    p = argparse.ArgumentParser(description="Stage prediction backtest for Bracket_Simulations")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("write-actuals", help="Write actual_participants.json per tournament")

    pa = sub.add_parser("analyze", help="Run analysis/ on all bracket outputs")
    pa.add_argument("--tournaments", nargs="*", default=HISTORICAL_TOURNAMENTS)

    pb = sub.add_parser("backtest", help="Write stage_prediction_backtest.md reports")
    pb.add_argument("--tournaments", nargs="*", default=HISTORICAL_TOURNAMENTS)

    pr = sub.add_parser("run-historical", help="Full pipeline: actuals, sims, analyze, backtest")
    pr.add_argument("--n-sims", type=int, default=200_000)
    pr.add_argument("--batch-size", type=int, default=1000)
    pr.add_argument("--seed", type=int, default=42)
    pr.add_argument("--no-reset", action="store_true")
    pr.add_argument("--skip-sims", action="store_true")
    pr.add_argument("-v", "--verbose", action="store_true", default=True)
    pr.add_argument("--tournaments", nargs="*", default=HISTORICAL_TOURNAMENTS)

    args = p.parse_args()
    if args.command == "write-actuals":
        write_all_actual_participants()
    elif args.command == "analyze":
        analyze_all_outputs(list(args.tournaments))
    elif args.command == "backtest":
        write_backtest_reports(list(args.tournaments))
    elif args.command == "run-historical":
        run_historical_pipeline(
            n_sims=args.n_sims,
            batch_size=args.batch_size,
            seed=args.seed,
            reset=not args.no_reset,
            skip_sims=args.skip_sims,
            verbose=args.verbose,
            tournaments=list(args.tournaments),
        )


if __name__ == "__main__":
    main()
