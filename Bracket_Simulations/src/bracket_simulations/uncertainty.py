from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from bracket_simulations.actual_results import EXPECTED_N


def block_bootstrap_delta(
    per_tournament_model: list[float],
    per_tournament_market: list[float],
    *,
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict[str, float | int]:
    """Bootstrap the mean (model - market) gap by resampling whole tournaments.

    Each list holds one value per tournament for a single (stage, metric),
    e.g. per-tournament recall = hits / EXPECTED_N[stage].
    """
    model = np.asarray(per_tournament_model, dtype=float)
    market = np.asarray(per_tournament_market, dtype=float)
    delta = model - market                      # paired per tournament
    n = len(delta)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))  # resample tournaments w/ replacement
    boot_means = delta[idx].mean(axis=1)
    return {
        "delta_mean": float(delta.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
        "n_tournaments": n,
        "n_model_better": int((delta > 0).sum()),
        "n_market_better": int((delta < 0).sum()),
        "significant": bool(np.percentile(boot_means, 2.5) > 0
                            or np.percentile(boot_means, 97.5) < 0),
    }


def _metric_from_probabilities(
    probs: dict[str, float],
    all_teams: list[str],
    actual_set: set[str],
    stage: str,
) -> dict[str, float]:
    n = EXPECTED_N[stage]
    ranked = sorted(all_teams, key=lambda team: probs[team], reverse=True)[:n]
    topn = set(ranked)
    brier_qualifiers = sum((probs[team] - 1.0) ** 2 for team in actual_set) / len(actual_set)
    brier = 0.0
    logloss = 0.0
    for team in all_teams:
        p = min(max(probs[team], 1e-15), 1.0 - 1e-15)
        y = 1.0 if team in actual_set else 0.0
        brier += (p - y) ** 2
        logloss += -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    return {
        "m1_recall": len(topn & actual_set) / n,
        "m2_brier_qualifiers": brier_qualifiers,
        "m5_brier": brier / len(all_teams),
        "m6_logloss": logloss / len(all_teams),
    }


def metric_mcse_from_sim_matrix(
    sim_matrix_path: Path,
    *,
    actual_at_least: dict[str, set[str]],
    min_chunks: int = 10,
    max_chunks: int = 25,
) -> dict[str, dict[str, float | int]]:
    sidecar_path = sim_matrix_path.with_name("sim_matrix_index.json")
    payload = np.load(sim_matrix_path)
    matrix = np.asarray(payload["matrix"], dtype=bool)
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    teams = [str(team) for team in sidecar["teams"]]
    stages = [str(stage) for stage in sidecar["stages"]]

    n_sims = int(matrix.shape[0])
    n_chunks = max(min_chunks, min(max_chunks, n_sims))
    chunk_size = max(1, n_sims // n_chunks)
    metric_names = ("m1_recall", "m2_brier_qualifiers", "m5_brier", "m6_logloss")
    out: dict[str, dict[str, float | int]] = {}

    for stage_idx, stage in enumerate(stages):
        actual_set = actual_at_least.get(stage, set())
        if not actual_set:
            continue
        chunk_metrics: dict[str, list[float]] = {name: [] for name in metric_names}
        for start in range(0, n_sims, chunk_size):
            stop = min(n_sims, start + chunk_size)
            chunk = matrix[start:stop, :, stage_idx].astype(float)
            probs = chunk.mean(axis=0)
            prob_map = {team: float(probs[idx]) for idx, team in enumerate(teams)}
            metrics = _metric_from_probabilities(prob_map, teams, actual_set, stage)
            for name in metric_names:
                chunk_metrics[name].append(metrics[name])
        out[stage] = {
            f"{name}_mcse": float(np.std(values, ddof=1) / np.sqrt(len(values)))
            if len(values) > 1
            else 0.0
            for name, values in chunk_metrics.items()
        }
        out[stage]["n_chunks"] = len(next(iter(chunk_metrics.values()), []))
        out[stage]["chunk_size"] = chunk_size
    return out
