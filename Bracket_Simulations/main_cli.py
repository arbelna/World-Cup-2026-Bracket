#!/usr/bin/env python3
"""Bracket_Simulations CLI — stage 3 of WorldCup2026 Bracket pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parent
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def cmd_sync_inputs(_: argparse.Namespace) -> None:
    script = STAGE_ROOT / "scripts" / "sync_inputs.ps1"
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True)


def cmd_build_data(_: argparse.Namespace) -> None:
    script = STAGE_ROOT / "scripts" / "build_bracket_data.py"
    subprocess.run([sys.executable, str(script)], check=True)


def cmd_precompute_pairs(args: argparse.Namespace) -> None:
    from bracket_simulations.config import list_tournament_config_names
    from bracket_simulations.model_variants import list_model_variant_ids
    from bracket_simulations.pairwise.precompute import precompute_for_config

    tournaments = [args.tournament] if args.tournament else list_tournament_config_names()
    variants = list_model_variant_ids() if args.all_variants else [args.variant]
    for t in tournaments:
        for variant in variants:
            precompute_for_config(t, variant_id=variant)


def cmd_simulate(args: argparse.Namespace) -> None:
    from bracket_simulations.run import main as sim_main

    argv = ["--tournament", args.tournament, "--mode", args.mode]
    if args.n_sims is not None:
        argv.extend(["--n-sims", str(args.n_sims)])
    if args.batch_size is not None:
        argv.extend(["--batch-size", str(args.batch_size)])
    if args.seed is not None:
        argv.extend(["--seed", str(args.seed)])
    if args.settings_tag is not None:
        argv.extend(["--settings-tag", str(args.settings_tag)])
    if args.reset:
        argv.append("--reset")
    if args.force_reset:
        argv.append("--force-reset")
    if args.verbose:
        argv.append("-v")
    if args.stop_after_group:
        argv.append("--stop-after-group")
    sim_main(argv)


def cmd_compare(args: argparse.Namespace) -> None:
    from bracket_simulations.compare import run_compare
    from bracket_simulations.paths import STAGE_ROOT

    json_out = Path(args.json_out) if args.json_out else STAGE_ROOT / "data" / "output" / "compare_summary.json"
    run_compare(json_out=json_out)


def cmd_backtest(args: argparse.Namespace) -> None:
    from bracket_simulations import prediction_backtest as pb

    tournaments = getattr(args, "tournaments", None)

    if args.backtest_cmd == "write-actuals":
        pb.write_all_actual_participants(list(tournaments) if tournaments else None)
    elif args.backtest_cmd == "analyze":
        pb.analyze_all_outputs(list(tournaments) if tournaments else None)
    elif args.backtest_cmd == "report":
        pb.write_backtest_reports(list(tournaments) if tournaments else None)
    elif args.backtest_cmd == "robustness":
        pb.write_robustness_reports(
            n_sims=args.n_sims,
            batch_size=args.batch_size,
            reset=not args.no_reset,
            verbose=args.verbose,
            tournaments=list(tournaments) if tournaments else None,
        )
    elif args.backtest_cmd == "run-historical":
        pb.run_historical_pipeline(
            n_sims=args.n_sims,
            batch_size=args.batch_size,
            seed=args.seed,
            reset=not args.no_reset,
            skip_sims=args.skip_sims,
            verbose=args.verbose,
            tournaments=list(tournaments) if tournaments else None,
        )


def cmd_run_all(args: argparse.Namespace) -> None:
    cmd_sync_inputs(args)
    cmd_build_data(args)
    cmd_precompute_pairs(argparse.Namespace(tournament=None))
    from bracket_simulations.config import list_tournament_config_names

    for t in list_tournament_config_names():
        for mode in ("market_all", "model_all"):
            sim_args = argparse.Namespace(
                tournament=t,
                mode=mode,
                n_sims=args.n_sims,
                batch_size=args.batch_size,
                seed=args.seed,
                reset=True,
                force_reset=False,
                verbose=args.verbose,
            )
            cmd_simulate(sim_args)
    cmd_compare(argparse.Namespace(json_out=None))
    from bracket_simulations import prediction_backtest as pb

    pb.write_all_actual_participants()
    pb.analyze_all_outputs()
    pb.write_backtest_reports()


def main() -> None:
    from bracket_simulations.config import list_tournament_config_names
    from bracket_simulations.model_variants import list_simulation_modes, list_model_variant_ids

    p = argparse.ArgumentParser(description="WorldCup2026 Bracket Bracket_Simulations")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("sync-inputs")
    sub.add_parser("build-data")

    pp = sub.add_parser("precompute-pairs")
    pp.add_argument("--tournament", choices=list_tournament_config_names())
    pp.add_argument("--variant", choices=list_model_variant_ids(), default="base")
    pp.add_argument("--all-variants", action="store_true")

    ps = sub.add_parser("simulate")
    ps.add_argument("--tournament", choices=list_tournament_config_names(), required=True)
    ps.add_argument("--mode", choices=list_simulation_modes(), required=True)
    ps.add_argument("--n-sims", type=int)
    ps.add_argument("--batch-size", type=int)
    ps.add_argument("--seed", type=int, default=42)
    ps.add_argument("--settings-tag", default=None)
    ps.add_argument("--reset", action="store_true")
    ps.add_argument("--force-reset", action="store_true")
    ps.add_argument("-v", "--verbose", action="store_true")
    ps.add_argument("--stop-after-group", action="store_true")

    pc = sub.add_parser("compare")
    pc.add_argument("--json-out", default=None)

    pbt = sub.add_parser("backtest", help="Actuals, analysis, and stage_prediction_backtest reports")
    pbt_sub = pbt.add_subparsers(dest="backtest_cmd", required=True)
    pbt_sub.add_parser("write-actuals")
    pba = pbt_sub.add_parser("analyze")
    pba.add_argument("--tournaments", nargs="*", default=None)
    pbr = pbt_sub.add_parser("report")
    pbr.add_argument("--tournaments", nargs="*", default=None)
    pbrob = pbt_sub.add_parser("robustness")
    pbrob.add_argument("--tournaments", nargs="*", default=None)
    pbrob.add_argument("--n-sims", type=int, default=200_000)
    pbrob.add_argument("--batch-size", type=int, default=10000)
    pbrob.add_argument("--no-reset", action="store_true")
    pbrob.add_argument("-v", "--verbose", action="store_true", default=True)
    pbrun = pbt_sub.add_parser("run-historical")
    pbrun.add_argument("--tournaments", nargs="*", default=None)
    pbrun.add_argument("--n-sims", type=int, default=200_000)
    pbrun.add_argument("--batch-size", type=int, default=10000)
    pbrun.add_argument("--seed", type=int, default=42)
    pbrun.add_argument("--no-reset", action="store_true")
    pbrun.add_argument("--skip-sims", action="store_true")
    pbrun.add_argument("-v", "--verbose", action="store_true", default=True)

    pa = sub.add_parser("run-all")
    pa.add_argument("--n-sims", type=int, default=200_000)
    pa.add_argument("--batch-size", type=int, default=10000)
    pa.add_argument("--seed", type=int, default=42)
    pa.add_argument("-v", "--verbose", action="store_true")

    args = p.parse_args()
    handlers = {
        "sync-inputs": cmd_sync_inputs,
        "build-data": cmd_build_data,
        "precompute-pairs": cmd_precompute_pairs,
        "simulate": cmd_simulate,
        "compare": cmd_compare,
        "backtest": cmd_backtest,
        "run-all": cmd_run_all,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
