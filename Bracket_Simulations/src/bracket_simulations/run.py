from __future__ import annotations

import argparse
import json
import logging
import random
import time

from bracket_simulations.aggregates import (
    load_state,
    merge_config_counts,
    merge_reach_counts,
    resolve_bracket_output_dir,
    save_run_metadata,
    save_state_atomic,
    settings_fingerprint,
    utc_run_id,
    write_probabilities_csv,
    write_settings_json,
    write_sim_matrix,
    write_stage_config_csv,
)
from bracket_simulations.config import load_tournament_config
from bracket_simulations.paths import stage_relative_path
from bracket_simulations.providers import resolve_prob_providers
from bracket_simulations.simulator.bracket_resolver import (
    load_groups,
    load_knockout_bracket,
    load_r32_scenarios,
)
from bracket_simulations.simulator.group_stage import GroupMatch
from bracket_simulations.simulator.simulator import run_single_simulation
from bracket_simulations.tournament_data import build_group_schedule, load_tournament_fixtures


def _setup_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")


def run_simulations(args: argparse.Namespace) -> None:
    cfg = load_tournament_config(args.tournament)
    alphas = dict(cfg.alphas)
    if args.alpha_knockout is not None:
        for stage in ("R16", "QF", "SF", "final", "third_place"):
            if stage in alphas:
                alphas[stage] = args.alpha_knockout
    if args.alpha_group_tie is not None:
        alphas["group_tie"] = args.alpha_group_tie

    mode = args.mode
    settings_tag = getattr(args, "settings_tag", None)
    settings_fp = settings_fingerprint(
        tournament=args.tournament,
        mode=mode,
        alphas=alphas,
        tag=settings_tag,
    )
    bracket_dir = resolve_bracket_output_dir(cfg.output_dir, mode=mode, settings_fp=settings_fp)
    bracket_dir.mkdir(parents=True, exist_ok=True)
    write_settings_json(
        bracket_dir / "settings.json",
        tournament=args.tournament,
        mode=mode,
        alphas=alphas,
        tag=settings_tag,
    )

    state_path = bracket_dir / "state.json"
    if args.reset and state_path.exists():
        state_path.unlink()

    state = load_state(state_path)
    if state.get("settings_fingerprint") and state["settings_fingerprint"] != settings_fp:
        if not (args.reset or args.force_reset):
            raise SystemExit(
                f"Settings fingerprint mismatch in {bracket_dir}. Use --reset or --force-reset."
            )
    if args.reset or args.force_reset or not state.get("settings_fingerprint"):
        state = {
            "total_sims": 0,
            "reach_counts": {},
            "config_counts": {},
            "settings_fingerprint": settings_fp,
            "settings": {
                "tournament": args.tournament,
                "mode": mode,
                "alphas": alphas,
                "tag": settings_tag,
            },
        }

    groups = load_groups(cfg.groups_file)
    bracket = load_knockout_bracket(cfg.knockout_bracket_file)
    fixtures = load_tournament_fixtures(cfg.fixtures_file, cfg.tournament_id)
    raw_group_schedule = build_group_schedule(groups, fixtures)
    group_fixtures = {
        label: [GroupMatch(team_a=a, team_b=b) for a, b in matches]
        for label, matches in raw_group_schedule.items()
    }
    scenarios_index = (
        load_r32_scenarios(cfg.r32_scenarios_file)
        if cfg.has_r32 and cfg.r32_scenarios_file is not None
        else None
    )
    all_teams = sorted({t for ts in groups.values() for t in ts})
    group_probs, ko_probs = resolve_prob_providers(cfg, mode, groups)
    rng = random.Random(args.seed)
    batch_size = args.batch_size
    n_sims = args.n_sims
    n_batches = (n_sims + batch_size - 1) // batch_size

    run_id = utc_run_id()
    t0 = time.perf_counter()
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting %s | mode=%s | n_sims=%d | batch_size=%d",
        args.tournament,
        mode,
        n_sims,
        batch_size,
    )

    sims_done = 0
    all_reaches: list[dict[str, str]] = []
    for batch_idx in range(n_batches):
        batch_start = time.perf_counter()
        this_batch = min(batch_size, n_sims - sims_done)
        batch_reaches: list[dict[str, str]] = []
        batch_participants: list[dict[str, tuple[str, ...]]] = []

        for _ in range(this_batch):
            outcome = run_single_simulation(
                groups,
                group_fixtures,
                group_probs,
                ko_probs,
                bracket,
                rng,
                scenarios_index=scenarios_index,
                best_third_qualifiers=cfg.best_third_qualifiers,
                stop_after_group=args.stop_after_group,
                alphas=alphas,
            )
            batch_reaches.append(outcome.stages)
            batch_participants.append(outcome.participants)

        merge_reach_counts(state, batch_reaches, cfg.stages_tracked)
        merge_config_counts(state, batch_participants)
        state["total_sims"] = int(state.get("total_sims", 0)) + this_batch
        save_state_atomic(state_path, state)
        all_reaches.extend(batch_reaches)

        sims_done += this_batch
        elapsed = time.perf_counter() - batch_start
        rate = this_batch / elapsed if elapsed > 0 else 0.0
        logger.info(
            "Batch %d/%d | sims=%d/%d | %.1f sims/s",
            batch_idx + 1,
            n_batches,
            sims_done,
            n_sims,
            rate,
        )

    total_elapsed = time.perf_counter() - t0
    write_probabilities_csv(
        bracket_dir / "team_stage_probabilities.csv", state, cfg.stages_tracked, all_teams
    )
    write_stage_config_csv(bracket_dir / "stage_config_probabilities.csv", state)
    write_sim_matrix(
        bracket_dir / "sim_matrix.npz",
        all_reaches,
        cfg.stages_tracked,
        all_teams,
    )

    meta = {
        "run_id": run_id,
        "tournament": args.tournament,
        "mode": mode,
        "alphas": alphas,
        "n_sims": n_sims,
        "batch_size": batch_size,
        "duration_sec": round(total_elapsed, 3),
        "seed": args.seed,
        "settings_tag": settings_tag,
        "settings_fingerprint": settings_fp,
        "bracket_dir": stage_relative_path(bracket_dir),
    }
    save_run_metadata(bracket_dir / "runs" / f"{run_id}.json", meta)
    logger.info("Done. total_sims=%d | bracket_dir=%s", state["total_sims"], stage_relative_path(bracket_dir))


def build_simulate_parser() -> argparse.ArgumentParser:
    from bracket_simulations.config import list_tournament_config_names

    p = argparse.ArgumentParser(description="Monte Carlo bracket simulation")
    p.add_argument("--tournament", choices=list_tournament_config_names(), required=True)
    from bracket_simulations.model_variants import list_simulation_modes

    p.add_argument("--mode", choices=list_simulation_modes(), required=True)
    p.add_argument("--n-sims", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--alpha-knockout", type=float, default=None)
    p.add_argument("--alpha-group-tie", type=float, default=None)
    p.add_argument("--settings-tag", default=None)
    p.add_argument("--reset", action="store_true")
    p.add_argument("--force-reset", action="store_true")
    p.add_argument("--stop-after-group", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    p = build_simulate_parser()
    args = p.parse_args(argv)
    cfg = load_tournament_config(args.tournament)
    if args.n_sims is None:
        args.n_sims = cfg.default_n_sims
    if args.batch_size is None:
        args.batch_size = cfg.default_batch_size
    _setup_logging(args.verbose)
    run_simulations(args)
