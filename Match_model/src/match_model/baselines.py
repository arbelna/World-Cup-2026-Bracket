from __future__ import annotations

import numpy as np

from match_model.rows import MatchRow
from match_model.targets import furthest_bookmaker_probs

# Not a predictive baseline: copies the soft label (median de-vigged market target) as the
# prediction. Useful as a target-oracle sanity check only; CE/Brier vs this reference are
# not meaningful model comparisons.
REFERENCE_MARKET_TARGET_ORACLE = "market_target_oracle"


def market_target_oracle_predict(rows: list[MatchRow]) -> np.ndarray:
    """Return target_soft unchanged (label-echo reference, not a forecast)."""
    return np.vstack([row.y_soft for row in rows])


def marginal_baseline_predict(train_rows: list[MatchRow], test_rows: list[MatchRow]) -> np.ndarray:
    canonical_train = [row for row in train_rows if not row.is_mirror]
    mean_probs = np.mean(np.vstack([row.y_soft for row in canonical_train]), axis=0)
    mean_probs = mean_probs / mean_probs.sum()
    return np.tile(mean_probs, (len(test_rows), 1))


def _draw_rates_by_stage(train_rows: list[MatchRow]) -> tuple[dict[str, float], float]:
    canonical = [row for row in train_rows if not row.is_mirror]
    pooled_draws: list[float] = []
    by_bucket: dict[str, list[float]] = {"group": [], "knockout": []}
    for row in canonical:
        draw_p = float(row.y_soft[1])
        pooled_draws.append(draw_p)
        bucket = "group" if row.stage == "group" else "knockout"
        by_bucket[bucket].append(draw_p)
    pooled = float(np.mean(pooled_draws)) if pooled_draws else 1.0 / 3.0
    rates = {
        bucket: float(np.mean(values)) if values else pooled
        for bucket, values in by_bucket.items()
    }
    return rates, pooled


def elo_baseline_predict(train_rows: list[MatchRow], test_rows: list[MatchRow]) -> np.ndarray:
    rates, pooled = _draw_rates_by_stage(train_rows)
    preds: list[np.ndarray] = []
    for row in test_rows:
        bucket = "group" if row.stage == "group" else "knockout"
        p_draw = rates.get(bucket, pooled)
        p_a_cond = 1.0 / (1.0 + 10.0 ** (-row.elo_diff / 400.0))
        p_b_cond = 1.0 - p_a_cond
        p_a_win = (1.0 - p_draw) * p_a_cond
        p_b_win = (1.0 - p_draw) * p_b_cond
        vec = np.array([p_a_win, p_draw, p_b_win], dtype=float)
        vec = np.clip(vec, 1e-15, None)
        preds.append(vec / vec.sum())
    return np.vstack(preds)


def market_dispersion_baseline_predict(test_rows: list[MatchRow]) -> np.ndarray:
    preds: list[np.ndarray] = []
    for row in test_rows:
        median = np.asarray(row.y_soft, dtype=float)
        if row.odds:
            furthest = furthest_bookmaker_probs(row.odds, median)
            preds.append(furthest if furthest is not None else median)
        else:
            preds.append(median)
    return np.vstack(preds)


def predict_baseline(
    name: str,
    train_rows: list[MatchRow],
    test_rows: list[MatchRow],
) -> np.ndarray:
    if name == REFERENCE_MARKET_TARGET_ORACLE:
        return market_target_oracle_predict(test_rows)
    if name == "marginal":
        return marginal_baseline_predict(train_rows, test_rows)
    if name == "elo":
        return elo_baseline_predict(train_rows, test_rows)
    if name == "market_dispersion":
        return market_dispersion_baseline_predict(test_rows)
    raise ValueError(f"Unknown baseline or reference: {name}")
