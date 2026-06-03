from __future__ import annotations

import numpy as np


def devig_odds_triple(a_odds: float, x_odds: float, b_odds: float) -> np.ndarray | None:
    odds = np.array([a_odds, x_odds, b_odds], dtype=float)
    if not np.all(np.isfinite(odds)) or np.any(odds <= 1.0):
        return None
    raw = 1.0 / odds
    total = raw.sum()
    if total <= 0.0:
        return None
    return raw / total


def median_odds_target(odds_rows: list[list[float]]) -> np.ndarray | None:
    probs: list[np.ndarray] = []
    for row in odds_rows:
        if len(row) != 3:
            continue
        prob = devig_odds_triple(float(row[0]), float(row[1]), float(row[2]))
        if prob is not None:
            probs.append(prob)
    if not probs:
        return None
    stacked = np.vstack(probs)
    median = np.median(stacked, axis=0)
    total = median.sum()
    if total <= 0.0:
        return None
    return median / total


def target_from_match(match: dict) -> np.ndarray | None:
    odds_rows = match.get("odds")
    if not odds_rows:
        return None
    return median_odds_target(odds_rows)


def furthest_bookmaker_probs(
    odds_rows: list[list[float]],
    median_target: np.ndarray,
) -> np.ndarray | None:
    vectors: list[np.ndarray] = []
    for row in odds_rows:
        if len(row) != 3:
            continue
        prob = devig_odds_triple(float(row[0]), float(row[1]), float(row[2]))
        if prob is not None:
            vectors.append(prob)
    if not vectors:
        return None
    median = np.asarray(median_target, dtype=float)
    errors = [float(np.mean(np.abs(vec - median))) for vec in vectors]
    return vectors[int(np.argmax(errors))]
