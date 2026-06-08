"""Recover CSV outputs from state.json and regenerate sim_matrix.npz (same seed)."""
from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parent.parent
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bracket_simulations.aggregates import (  # noqa: E402
    load_state,
    resolve_bracket_output_dir,
    settings_fingerprint,
    write_probabilities_csv,
    write_sim_matrix,
    write_stage_config_csv,
)
from bracket_simulations.config import load_tournament_config  # noqa: E402
from bracket_simulations.providers import resolve_prob_providers  # noqa: E402
from bracket_simulations.simulator.bracket_resolver import (  # noqa: E402
    load_groups,
    load_knockout_bracket,
    load_r32_scenarios,
)
from bracket_simulations.simulator.simulator import run_single_simulation  # noqa: E402

TOURNAMENT = "wc2026"
MODE = "model_all"
N_SIMS = 1_000_000
SEED = 42
BATCH_LOG = 50_000


def _replace_with_retry(src: Path, dst: Path, *, attempts: int = 60, delay_sec: float = 10.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            os.replace(src, dst)
            print(f"Replaced {dst.name}")
            return
        except OSError as exc:
            if attempt == attempts:
                raise SystemExit(
                    f"Could not replace {dst} after {attempts} attempts ({exc}). "
                    f"Close any app using that file, then run:\n"
                    f'  move /Y "{src}" "{dst}"'
                ) from exc
            print(f"  {dst.name} locked ({exc}); retry {attempt}/{attempts} in {delay_sec:.0f}s...")
            time.sleep(delay_sec)


def main() -> None:
    cfg = load_tournament_config(TOURNAMENT)
    alphas = dict(cfg.alphas)
    fp = settings_fingerprint(tournament=TOURNAMENT, mode=MODE, alphas=alphas)
    bracket_dir = resolve_bracket_output_dir(cfg.output_dir, mode=MODE, settings_fp=fp)
    state_path = bracket_dir / "state.json"
    state = load_state(state_path)
    total = int(state.get("total_sims", 0))
    if total != N_SIMS:
        raise SystemExit(f"Expected state total_sims={N_SIMS}, got {total}")

    groups = load_groups(cfg.groups_file)
    all_teams = sorted({t for ts in groups.values() for t in ts})

    probs_tmp = bracket_dir / "team_stage_probabilities.csv.new"
    configs_tmp = bracket_dir / "stage_config_probabilities.csv.new"
    print(f"Writing CSVs from state ({total:,} sims)...")
    write_probabilities_csv(probs_tmp, state, cfg.stages_tracked, all_teams)
    write_stage_config_csv(configs_tmp, state)
    print("CSVs written to .new files.")

    bracket = load_knockout_bracket(cfg.knockout_bracket_file)
    scenarios_index = (
        load_r32_scenarios(cfg.r32_scenarios_file)
        if cfg.has_r32 and cfg.r32_scenarios_file is not None
        else None
    )
    group_probs, ko_probs = resolve_prob_providers(cfg, MODE, groups)
    rng = random.Random(SEED)

    print(f"Regenerating sim_matrix.npz ({N_SIMS:,} sims, seed={SEED})...")
    t0 = time.perf_counter()
    all_reaches: list[dict[str, str]] = []
    for i in range(N_SIMS):
        outcome = run_single_simulation(
            groups,
            group_probs,
            ko_probs,
            bracket,
            rng,
            scenarios_index=scenarios_index,
            best_third_qualifiers=cfg.best_third_qualifiers,
            stop_after_group=False,
            alphas=alphas,
        )
        all_reaches.append(outcome.stages)
        if (i + 1) % BATCH_LOG == 0:
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0.0
            print(f"  {i + 1:,}/{N_SIMS:,} | {rate:.1f} sims/s")

    write_sim_matrix(
        bracket_dir / "sim_matrix.npz",
        all_reaches,
        cfg.stages_tracked,
        all_teams,
    )
    elapsed = time.perf_counter() - t0
    print(f"sim_matrix done in {elapsed:.1f}s.")

    _replace_with_retry(probs_tmp, bracket_dir / "team_stage_probabilities.csv")
    _replace_with_retry(configs_tmp, bracket_dir / "stage_config_probabilities.csv")
    print(f"All outputs ready in {bracket_dir}")


if __name__ == "__main__":
    main()
