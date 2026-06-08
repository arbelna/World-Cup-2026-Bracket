from __future__ import annotations

import math

from bracket_simulations.actual_results import STAGES, build_actual_outcome
from bracket_simulations.compare import _load_preds, probabilities_csv

# Wider fixed bins to handle sparse high-probability buckets.
BIN_EDGES = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.01]


def collect_reliability_pairs(tournaments: list[str], mode: str) -> list[tuple[float, int]]:
    """Pool (predicted p_at_least, actual 0/1) over all teams x stages x tournaments."""
    pairs: list[tuple[float, int]] = []
    for t in tournaments:
        actual = build_actual_outcome(t)
        preds = _load_preds(probabilities_csv(t, mode))
        for stage in STAGES:
            reached = actual.actual_at_least[stage]
            for team, row in preds.items():
                p = float(row[f"p_at_least_{stage}"])
                pairs.append((p, 1 if team in reached else 0))
    return pairs


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for an observed proportion (handles small n)."""
    if n == 0:
        return (0.0, 0.0)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def reliability_table(
    pairs: list[tuple[float, int]],
    bin_edges: list[float],
) -> tuple[list[dict], float]:
    """Return per-bin rows + Expected Calibration Error (n-weighted mean |gap|)."""
    rows: list[dict] = []
    tot_gap = 0.0
    tot_n = 0
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        sub = [(p, y) for (p, y) in pairs if lo <= p < hi]
        if not sub:
            continue
        n = len(sub)
        k = sum(y for _, y in sub)
        avg_pred = sum(p for p, _ in sub) / n
        observed = k / n
        ci_low, ci_high = _wilson(k, n)
        rows.append({
            "lo": lo, "hi": hi, "n": n,
            "avg_pred": avg_pred, "observed": observed,
            "gap": avg_pred - observed,
            "obs_ci_low": ci_low, "obs_ci_high": ci_high,
        })
        tot_gap += abs(avg_pred - observed) * n
        tot_n += n
    ece = tot_gap / tot_n if tot_n else float("nan")
    return rows, ece
