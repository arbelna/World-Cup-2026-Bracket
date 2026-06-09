from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from match_model.baselines import REFERENCE_MARKET_TARGET_ORACLE, predict_baseline
from match_model.cv import LotoFold, leave_one_tournament_out
from match_model.metrics import (
    METRIC_NAMES,
    aggregate_fold_metrics,
    evaluate_probs,
    evaluate_probs_single,
    weighted_fold_metric,
)
from match_model.model_catboost import (
    CatBoostCore7Model,
    FoldScaler,
    rows_to_feature_matrix,
    rows_to_label_matrix,
)
from match_model.paths import STAGE_ROOT
from match_model.rows import CORE7_FEATURE_NAMES, MatchRow, build_rows_with_mirrors

PREDICTIVE_BASELINE_NAMES: tuple[str, ...] = ("elo", "marginal", "market_dispersion")
REFERENCE_EXPERIMENT_ID = "reference__market_target_oracle"
CATBOOST_EXPERIMENT_ID = "catboost_loto_core7"


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_id: str
    model_name: str
    baseline_name: str | None = None
    is_reference: bool = False
    feature_names: tuple[str, ...] | None = None


ELO_ONLY_FEATURES: tuple[str, ...] = ("elo_diff",)
ELO_PLUS_VALUES_FEATURES: tuple[str, ...] = (
    "elo_diff",
    "z_log_top_15_average_value_team_a",
    "z_log_top_15_average_value_team_b",
)
MINUS_VALUES_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if not name.startswith("z_log_")
)
MINUS_CONFED_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if "confederation" not in name
)
MINUS_STAGE_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if name != "stage_binary"
)
MINUS_HOST_FEATURES: tuple[str, ...] = tuple(
    name for name in CORE7_FEATURE_NAMES if name != "host_diff"
)


def experiment_specs() -> list[ExperimentSpec]:
    specs = [
        ExperimentSpec(
            experiment_id=CATBOOST_EXPERIMENT_ID,
            model_name="catboost",
            feature_names=CORE7_FEATURE_NAMES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_elo_only",
            model_name="catboost",
            feature_names=ELO_ONLY_FEATURES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_elo_plus_values",
            model_name="catboost",
            feature_names=ELO_PLUS_VALUES_FEATURES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_minus_values",
            model_name="catboost",
            feature_names=MINUS_VALUES_FEATURES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_minus_confed",
            model_name="catboost",
            feature_names=MINUS_CONFED_FEATURES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_minus_stage",
            model_name="catboost",
            feature_names=MINUS_STAGE_FEATURES,
        ),
        ExperimentSpec(
            experiment_id="catboost_loto_minus_host",
            model_name="catboost",
            feature_names=MINUS_HOST_FEATURES,
        )
    ]
    for baseline in PREDICTIVE_BASELINE_NAMES:
        specs.append(
            ExperimentSpec(
                experiment_id=f"baseline__{baseline}",
                model_name="baseline",
                baseline_name=baseline,
            )
        )
    specs.append(
        ExperimentSpec(
            experiment_id=REFERENCE_EXPERIMENT_ID,
            model_name="reference",
            baseline_name=REFERENCE_MARKET_TARGET_ORACLE,
            is_reference=True,
        )
    )
    return specs


def _relpath(path: Path) -> str:
    try:
        return path.relative_to(STAGE_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _build_prediction_rows(
    spec: ExperimentSpec,
    fold: LotoFold,
    y_pred: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(fold.test_rows):
        pred = y_pred[idx]
        single = evaluate_probs_single(row.y_soft, pred)
        rows.append(
            {
                "experiment_id": spec.experiment_id,
                "held_out_competition": fold.held_out_competition,
                "match_id": row.match_id,
                "team_a": row.team_a,
                "team_b": row.team_b,
                "stage": row.stage,
                "elo_diff": row.elo_diff,
                "target_a": float(row.y_soft[0]),
                "target_draw": float(row.y_soft[1]),
                "target_b": float(row.y_soft[2]),
                "pred_a": float(pred[0]),
                "pred_draw": float(pred[1]),
                "pred_b": float(pred[2]),
                "ce": single["ce"],
                "brier": single["brier"],
                "mae_macro": single["mae_macro"],
            }
        )
    return rows


def run_single_fold(
    spec: ExperimentSpec,
    fold: LotoFold,
    *,
    random_state: int = 42,
    catboost_train_dir: Path | None = None,
) -> dict[str, Any]:
    train_rows = fold.train_rows
    test_rows = fold.test_rows
    y_true = np.vstack([row.y_soft for row in test_rows])

    if spec.baseline_name is not None:
        y_pred = predict_baseline(spec.baseline_name, train_rows, test_rows)
    else:
        feature_names = spec.feature_names or CORE7_FEATURE_NAMES
        x_train = rows_to_feature_matrix(train_rows, feature_names)
        y_train = rows_to_label_matrix(train_rows)
        x_test = rows_to_feature_matrix(test_rows, feature_names)
        scaler = FoldScaler.fit(x_train)
        x_train_s = scaler.transform(x_train)
        x_test_s = scaler.transform(x_test)
        model = CatBoostCore7Model(
            random_state=random_state,
            train_dir=catboost_train_dir,
        ).fit(x_train_s, y_train)
        model.feature_names = feature_names
        y_pred = model.predict_proba(x_test_s)

    metrics = evaluate_probs(y_true, y_pred)
    return {
        "held_out_competition": fold.held_out_competition,
        "n_test_matches": len(test_rows),
        **metrics,
        "predictions": _build_prediction_rows(spec, fold, y_pred),
    }


def run_experiment(
    spec: ExperimentSpec,
    rows: list[MatchRow],
    *,
    show_progress: bool = True,
    random_state: int = 42,
    catboost_train_dir: Path | None = None,
) -> dict[str, Any]:
    folds = leave_one_tournament_out(rows)
    fold_iter: Any = folds
    if show_progress:
        fold_iter = tqdm(folds, desc=f"  {spec.experiment_id}", leave=False, unit="fold")

    per_fold = [
        run_single_fold(
            spec,
            fold,
            random_state=random_state,
            catboost_train_dir=catboost_train_dir,
        )
        for fold in fold_iter
    ]
    summary_metrics = {metric: aggregate_fold_metrics(per_fold, metric) for metric in METRIC_NAMES}
    summary_metrics["weighted_ce"] = weighted_fold_metric(per_fold, "ce")
    summary_metrics["weighted_brier"] = weighted_fold_metric(per_fold, "brier")
    summary_metrics["weighted_mae_macro"] = weighted_fold_metric(per_fold, "mae_macro")

    all_predictions: list[dict[str, Any]] = []
    for fold in per_fold:
        all_predictions.extend(fold["predictions"])

    return {
        "experiment_id": spec.experiment_id,
        "model_name": spec.model_name,
        "baseline_name": spec.baseline_name,
        "is_reference": spec.is_reference,
        "feature_names": list(spec.feature_names or CORE7_FEATURE_NAMES),
        "per_fold": [{k: v for k, v in fold.items() if k != "predictions"} for fold in per_fold],
        "summary": summary_metrics,
        "predictions": all_predictions,
    }


def load_dataset_matches(dataset_path: Path) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = json.loads(dataset_path.read_text(encoding="utf-8"))
    complete: list[dict[str, Any]] = []
    for match in matches:
        if match.get("target_soft") is not None:
            complete.append(match)
    return complete


def run_loto_evaluation(
    dataset_path: Path,
    *,
    show_progress: bool = True,
    random_seed: int = 42,
    bootstrap_seed: int = 42,
    catboost_train_dir: Path | None = None,
) -> dict[str, Any]:
    np.random.seed(random_seed)
    random.seed(random_seed)

    matches = load_dataset_matches(dataset_path)
    rows = build_rows_with_mirrors(matches)
    specs = experiment_specs()

    results: list[dict[str, Any]] = []
    exp_iter: Any = specs
    if show_progress:
        exp_iter = tqdm(specs, desc="LOTO experiments", unit="exp")

    for spec in exp_iter:
        result = run_experiment(
            spec,
            rows,
            show_progress=show_progress,
            random_state=random_seed,
            catboost_train_dir=catboost_train_dir,
        )
        results.append(result)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": _relpath(dataset_path),
        "n_matches": len(matches),
        "n_rows_with_mirrors": len(rows),
        "n_folds": len(leave_one_tournament_out(rows)),
        "feature_names": list(CORE7_FEATURE_NAMES),
        "bootstrap_seed": bootstrap_seed,
        "experiments": results,
    }


def run_holdout_evaluation(
    *,
    train_dataset_path: Path,
    test_dataset_path: Path,
    held_out_competition: str,
    show_progress: bool = True,
    random_seed: int = 42,
    bootstrap_seed: int = 42,
    catboost_train_dir: Path | None = None,
) -> dict[str, Any]:
    np.random.seed(random_seed)
    random.seed(random_seed)

    train_matches = load_dataset_matches(train_dataset_path)
    test_matches = load_dataset_matches(test_dataset_path)
    train_rows = build_rows_with_mirrors(train_matches)
    test_rows_all = build_rows_with_mirrors(test_matches)
    test_rows = [row for row in test_rows_all if not row.is_mirror]

    fold = LotoFold(
        held_out_competition=held_out_competition,
        train_rows=train_rows,
        test_rows=test_rows,
    )
    specs = experiment_specs()
    results: list[dict[str, Any]] = []
    exp_iter: Any = specs
    if show_progress:
        exp_iter = tqdm(specs, desc="Holdout experiments", unit="exp")
    for spec in exp_iter:
        one_fold = run_single_fold(
            spec,
            fold,
            random_state=random_seed,
            catboost_train_dir=catboost_train_dir,
        )
        summary_metrics = {metric: aggregate_fold_metrics([one_fold], metric) for metric in METRIC_NAMES}
        summary_metrics["weighted_ce"] = float(one_fold["ce"])
        summary_metrics["weighted_brier"] = float(one_fold["brier"])
        summary_metrics["weighted_mae_macro"] = float(one_fold["mae_macro"])
        results.append(
            {
                "experiment_id": spec.experiment_id,
                "model_name": spec.model_name,
                "baseline_name": spec.baseline_name,
                "is_reference": spec.is_reference,
                "feature_names": list(spec.feature_names or CORE7_FEATURE_NAMES),
                "per_fold": [{k: v for k, v in one_fold.items() if k != "predictions"}],
                "summary": summary_metrics,
                "predictions": one_fold["predictions"],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "single_holdout",
        "dataset_path": _relpath(train_dataset_path),
        "test_dataset_path": _relpath(test_dataset_path),
        "n_matches": len(train_matches) + len(test_matches),
        "n_rows_with_mirrors": len(train_rows) + len(test_rows_all),
        "n_folds": 1,
        "held_out_competition": held_out_competition,
        "feature_names": list(CORE7_FEATURE_NAMES),
        "bootstrap_seed": bootstrap_seed,
        "experiments": results,
    }
