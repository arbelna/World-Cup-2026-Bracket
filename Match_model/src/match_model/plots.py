from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from match_model.loto import CATBOOST_EXPERIMENT_ID, REFERENCE_EXPERIMENT_ID


def _axis_limits(values: list[float], pad_ratio: float = 0.12) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    span = hi - lo
    if span <= 0:
        span = max(abs(lo), 1e-6) * 0.05
    pad = span * pad_ratio
    return lo - pad, hi + pad


def _horizontal_metric_plot(
    rows: list[dict[str, Any]],
    metric_key: str,
    title: str,
    output_path: Path,
    *,
    lower_is_better: bool,
) -> None:
    sorted_rows = sorted(rows, key=lambda row: row[metric_key], reverse=not lower_is_better)
    labels = [row["experiment_id"] for row in sorted_rows]
    values = [row[metric_key] for row in sorted_rows]

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.35)))
    ax.barh(labels, values, color="#4C78A8")
    ax.set_title(title)
    ax.set_xlabel(metric_key)
    x_lo, x_hi = _axis_limits(values)
    ax.set_xlim(x_lo, x_hi)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _per_fold_ce_plot(catboost_result: dict[str, Any], output_path: Path) -> None:
    per_fold = catboost_result.get("per_fold") or []
    if not per_fold:
        return
    comps = [f["held_out_competition"] for f in per_fold]
    ces = [f["ce"] for f in per_fold]

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(comps))
    ax.bar(x, ces, color="#F58518")
    ax.set_title("CatBoost core7 - per-fold cross-entropy (held-out tournament)")
    ax.set_ylabel("ce")
    ax.set_xticks(x)
    ax.set_xticklabels(comps, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _model_vs_baseline_delta_plot(
    payload: dict[str, Any],
    *,
    baseline_experiment_id: str,
    output_path: Path,
    title: str,
    ylabel: str,
) -> None:
    model = next(
        (e for e in payload["experiments"] if e["experiment_id"] == CATBOOST_EXPERIMENT_ID),
        None,
    )
    baseline = next(
        (e for e in payload["experiments"] if e["experiment_id"] == baseline_experiment_id),
        None,
    )
    if not model or not baseline:
        return

    model_by_comp = {f["held_out_competition"]: f["ce"] for f in model["per_fold"]}
    base_by_comp = {f["held_out_competition"]: f["ce"] for f in baseline["per_fold"]}
    comps = sorted(model_by_comp.keys())
    deltas = [model_by_comp[c] - base_by_comp[c] for c in comps]

    colors = ["#E45756" if d > 0 else "#54A24B" for d in deltas]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(comps))
    ax.bar(x, deltas, color=colors)
    ax.axhline(0.0, color="#888888", linewidth=1, linestyle="--")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(comps, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _reliability_plot(catboost_result: dict[str, Any], output_path: Path) -> None:
    predictions = catboost_result.get("predictions") or []
    if not predictions:
        return

    bins = np.linspace(0.0, 1.0, 11)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    labels = ("Home win (A)", "Draw", "Away win (B)")
    target_keys = ("target_a", "target_draw", "target_b")
    pred_keys = ("pred_a", "pred_draw", "pred_b")

    for ax, label, t_key, p_key in zip(axes, labels, target_keys, pred_keys, strict=True):
        preds = np.array([row[p_key] for row in predictions], dtype=float)
        targets = np.array([row[t_key] for row in predictions], dtype=float)
        bin_idx = np.digitize(preds, bins) - 1
        bin_centers: list[float] = []
        observed: list[float] = []
        for b in range(len(bins) - 1):
            mask = bin_idx == b
            if not np.any(mask):
                continue
            bin_centers.append(float(np.mean(preds[mask])))
            observed.append(float(np.mean(targets[mask])))
        ax.plot([0, 1], [0, 1], "--", color="#888888", linewidth=1)
        ax.scatter(bin_centers, observed, color="#4C78A8")
        ax.set_title(label)
        ax.set_xlabel("Predicted probability")
        ax.set_ylabel("Observed frequency")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    fig.suptitle("Reliability - CatBoost core7 (all LOTO test predictions)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def write_loto_plots(
    payload: dict[str, Any],
    plots_dir: Path,
    *,
    catboost_result: dict[str, Any],
) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    predictive_rows = [
        {
            "experiment_id": item["experiment_id"],
            "weighted_ce": item["summary"]["weighted_ce"],
            "weighted_brier": item["summary"]["weighted_brier"],
        }
        for item in payload["experiments"]
        if not item.get("is_reference")
    ]

    _horizontal_metric_plot(
        predictive_rows,
        "weighted_ce",
        "Weighted cross-entropy - CatBoost and predictive baselines",
        plots_dir / "leaderboard_ce.png",
        lower_is_better=True,
    )
    _horizontal_metric_plot(
        predictive_rows,
        "weighted_brier",
        "Weighted Brier score - CatBoost and predictive baselines",
        plots_dir / "leaderboard_brier.png",
        lower_is_better=True,
    )
    _per_fold_ce_plot(catboost_result, plots_dir / "per_fold_ce_catboost_core7.png")
    _model_vs_baseline_delta_plot(
        payload,
        baseline_experiment_id="baseline__elo",
        output_path=plots_dir / "catboost_vs_elo_ce_delta.png",
        title="CatBoost vs Elo baseline - CE delta by tournament (negative = model better)",
        ylabel="ce_catboost - ce_elo",
    )
    _model_vs_baseline_delta_plot(
        payload,
        baseline_experiment_id=REFERENCE_EXPERIMENT_ID,
        output_path=plots_dir / "catboost_vs_target_oracle_ce_delta.png",
        title="CatBoost vs target oracle - CE delta (oracle echoes soft labels)",
        ylabel="ce_catboost - ce_target_oracle",
    )
    _reliability_plot(catboost_result, plots_dir / "reliability_catboost_core7.png")
