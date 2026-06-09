"""Stage prediction backtest reports (market_all vs model_all)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bracket_simulations.actual_results import EXPECTED_N, STAGES, build_actual_outcome
from bracket_simulations.uncertainty import block_bootstrap_delta, metric_mcse_from_sim_matrix
from bracket_simulations.aggregates import (
    load_state,
    resolve_bracket_output_dir,
    settings_fingerprint,
    top_config_for_stage,
)
from bracket_simulations.analysis import analyze_bracket_dir, combos_for_stage, cumulative_coverage
from bracket_simulations.calibration import (
    BIN_EDGES,
    collect_reliability_pairs,
    collect_reliability_pairs_by_stage,
    reliability_table,
)
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
from bracket_simulations.robustness import (
    build_robustness_payload,
    load_robustness_payload,
    write_robustness_payload,
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


def aggregate_with_uncertainty(rows: list[dict]) -> dict[str, dict[str, dict]]:
    """Bootstrap model-minus-market gap for recall, all-team Brier (M5), and log loss (M6), keyed by stage."""
    out: dict[str, dict[str, dict]] = {}
    for stage in STAGES:
        n = EXPECTED_N[stage]
        recall_model  = [r["model"][stage]["topn_hits"]  / n for r in rows]
        recall_market = [r["market"][stage]["topn_hits"] / n for r in rows]
        brier_model   = [r["model"][stage]["brier"]    for r in rows]
        brier_market  = [r["market"][stage]["brier"]   for r in rows]
        ll_model      = [r["model"][stage]["logloss"]  for r in rows]
        ll_market     = [r["market"][stage]["logloss"] for r in rows]
        out[stage] = {
            "recall":   block_bootstrap_delta(recall_model,  recall_market),
            "brier":    block_bootstrap_delta(brier_model,   brier_market),
            "logloss":  block_bootstrap_delta(ll_model,      ll_market),
        }
    return out


def build_report(tournaments: list[str]) -> tuple[list[dict], str, dict, dict, dict]:
    rows: list[dict] = []
    mcse: dict[str, dict[str, dict[str, dict[str, float | int]]]] = {
        mode: {} for mode in MODES
    }
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

        for mode in MODES:
            fp = settings_fingerprint(tournament=tournament, mode=mode, alphas=dict(cfg.alphas))
            bracket_dir = resolve_bracket_output_dir(cfg.output_dir, mode=mode, settings_fp=fp)
            sim_matrix_path = bracket_dir / "sim_matrix.npz"
            if sim_matrix_path.exists():
                mcse[mode][tournament] = metric_mcse_from_sim_matrix(
                    sim_matrix_path,
                    actual_at_least=actual.actual_at_least,
                )

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

    uncertainty = aggregate_with_uncertainty(rows)

    calibration: dict[str, dict] = {}
    for mode in MODES:
        pairs = collect_reliability_pairs(tournaments, mode)
        pooled_rows, pooled_ece = reliability_table(pairs, BIN_EDGES)
        by_stage_pairs = collect_reliability_pairs_by_stage(tournaments, mode)
        by_stage = {
            stage: reliability_table(stage_pairs, BIN_EDGES)
            for stage, stage_pairs in by_stage_pairs.items()
        }
        calibration[mode] = {
            "pooled_rows": pooled_rows,
            "pooled_ece": pooled_ece,
            "by_stage": by_stage,
    }

    md = render_backtest_markdown(
        rows,
        uncertainty=uncertainty,
        calibration=calibration,
        mcse=mcse,
    )
    return rows, md, uncertainty, calibration, mcse


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
    data, detailed_md, uncertainty, calibration, mcse = build_report(tlist)
    robustness = load_robustness_payload()
    if robustness is not None:
        detailed_md = render_backtest_markdown(
            data,
            uncertainty=uncertainty,
            calibration=calibration,
            mcse=mcse,
            robustness=robustness,
        )
    summary_path = DATA_OUTPUT / "stage_prediction_backtest.md"
    summary_path.write_text(detailed_md + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}")
    root_results = STAGE_ROOT / "results.md"
    root_results.write_text(
        render_summary_markdown(
            data,
            uncertainty=uncertainty,
            calibration=calibration,
            mcse=mcse,
            robustness=robustness,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {root_results}")
    json_path = DATA_OUTPUT / "stage_prediction_backtest.json"
    json_path.write_text(
        json.dumps(
            {
                "rows": data,
                "uncertainty": uncertainty,
                "calibration": calibration,
                "mcse": mcse,
                "robustness": robustness,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {json_path}")


def write_robustness_reports(
    *,
    n_sims: int = 200_000,
    batch_size: int = 1000,
    reset: bool = True,
    verbose: bool = True,
    tournaments: list[str] | None = None,
) -> None:
    tlist = tournaments or HISTORICAL_TOURNAMENTS
    payload = build_robustness_payload(
        tlist,
        n_sims=n_sims,
        batch_size=batch_size,
        reset=reset,
        verbose=verbose,
    )
    out = write_robustness_payload(payload)
    print(f"Wrote {out}")
    write_backtest_reports(tlist)


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
                settings_tag=None,
                reset=reset,
                force_reset=False,
                stop_after_group=False,
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

    ps = sub.add_parser("robustness", help="Run model-variant, seed, and alpha robustness backtests")
    ps.add_argument("--tournaments", nargs="*", default=HISTORICAL_TOURNAMENTS)
    ps.add_argument("--n-sims", type=int, default=200_000)
    ps.add_argument("--batch-size", type=int, default=1000)
    ps.add_argument("--no-reset", action="store_true")
    ps.add_argument("-v", "--verbose", action="store_true", default=True)

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
    elif args.command == "robustness":
        write_robustness_reports(
            n_sims=args.n_sims,
            batch_size=args.batch_size,
            reset=not args.no_reset,
            verbose=args.verbose,
            tournaments=list(args.tournaments),
        )
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
