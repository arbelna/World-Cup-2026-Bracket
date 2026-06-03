from __future__ import annotations

from typing import Any

import numpy as np

PROB_EPS = 1e-15
METRIC_NAMES = ("ce", "brier", "mae_macro", "avg_prob_error_pp")


def normalize_probs(probs: np.ndarray) -> np.ndarray:
    clipped = np.clip(probs, PROB_EPS, None)
    return clipped / clipped.sum(axis=1, keepdims=True)


def soft_cross_entropy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    pred = normalize_probs(y_pred)
    return float(-np.mean(np.sum(y_true * np.log(pred), axis=1)))


def brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    pred = normalize_probs(y_pred)
    return float(np.mean(np.sum((pred - y_true) ** 2, axis=1)))


def mae_per_class(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    pred = normalize_probs(y_pred)
    mae = np.mean(np.abs(pred - y_true), axis=0)
    return {
        "mae_a": float(mae[0]),
        "mae_draw": float(mae[1]),
        "mae_b": float(mae[2]),
        "mae_macro": float(np.mean(mae)),
    }


def avg_prob_error_pp(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    pred = normalize_probs(y_pred)
    return float(100.0 * np.mean(np.abs(pred - y_true)))


def evaluate_probs(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = mae_per_class(y_true, y_pred)
    return {
        "ce": soft_cross_entropy(y_true, y_pred),
        "brier": brier_score(y_true, y_pred),
        **mae,
        "avg_prob_error_pp": avg_prob_error_pp(y_true, y_pred),
    }


def evaluate_probs_single(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_t = np.asarray(y_true, dtype=float).reshape(1, 3)
    y_p = np.asarray(y_pred, dtype=float).reshape(1, 3)
    return evaluate_probs(y_t, y_p)


def bootstrap_ci(
    fold_values: list[float],
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> dict[str, float]:
    if not fold_values:
        return {
            "mean": float("nan"),
            "std": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
        }
    arr = np.asarray(fold_values, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(arr)
    samples = rng.choice(arr, size=(n_bootstrap, n), replace=True)
    means = samples.mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if n > 1 else 0.0,
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
    }


def aggregate_fold_metrics(per_fold: list[dict[str, Any]], metric_name: str) -> dict[str, float]:
    values = [float(item[metric_name]) for item in per_fold]
    return bootstrap_ci(values)


def weighted_fold_metric(per_fold: list[dict[str, Any]], metric_name: str) -> float:
    weights = np.array([float(item["n_test_matches"]) for item in per_fold], dtype=float)
    values = np.array([float(item[metric_name]) for item in per_fold], dtype=float)
    if weights.sum() <= 0:
        return float("nan")
    return float(np.average(values, weights=weights))
