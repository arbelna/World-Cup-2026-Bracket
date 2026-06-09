from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from match_model.metrics import METRIC_NAMES
from match_model.plots import write_loto_plots
from match_model.results_report import write_results_markdown


def _leaderboard_row(result: dict[str, Any]) -> dict[str, Any]:
    summary = result["summary"]
    row = {
        "experiment_id": result["experiment_id"],
        "model_name": result["model_name"],
        "baseline_name": result.get("baseline_name") or "",
        "is_reference": bool(result.get("is_reference")),
        "n_features": len(result.get("feature_names") or []),
        "weighted_ce": summary["weighted_ce"],
        "weighted_brier": summary["weighted_brier"],
        "weighted_mae_macro": summary["weighted_mae_macro"],
    }
    for metric in METRIC_NAMES:
        stats = summary[metric]
        row[f"{metric}_mean"] = stats["mean"]
        row[f"{metric}_std"] = stats["std"]
        row[f"{metric}_ci_low"] = stats["ci_low"]
        row[f"{metric}_ci_high"] = stats["ci_high"]
    return row


def write_loto_outputs(
    payload: dict[str, Any],
    output_dir: Path,
    *,
    output_prefix: str = "loto_eval",
    dataset_path: Path | None = None,
    write_results_md: bool = True,
) -> dict[str, Path]:
    from match_model.paths import DEFAULT_DATASET_PATH, STAGE_ROOT

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    results_path = output_dir / f"{output_prefix}_results.json"
    serializable = {
        **payload,
        "experiments": [
            {k: v for k, v in item.items() if k != "predictions"}
            for item in payload["experiments"]
        ],
    }
    results_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    paths["results_json"] = results_path

    leaderboard_rows = [_leaderboard_row(item) for item in payload["experiments"]]
    leaderboard_path = output_dir / f"{output_prefix}_leaderboard.csv"
    if leaderboard_rows:
        with leaderboard_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(leaderboard_rows[0].keys()))
            writer.writeheader()
            writer.writerows(leaderboard_rows)
    paths["leaderboard_csv"] = leaderboard_path

    per_fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    for result in payload["experiments"]:
        prediction_rows.extend(result.get("predictions") or [])
        for fold in result.get("per_fold") or []:
            per_fold_rows.append(
                {
                    "experiment_id": result["experiment_id"],
                    "model_name": result["model_name"],
                    "baseline_name": result.get("baseline_name") or "",
                    "is_reference": bool(result.get("is_reference")),
                    "held_out_competition": fold["held_out_competition"],
                    "n_test_matches": fold["n_test_matches"],
                    **{metric: fold[metric] for metric in METRIC_NAMES},
                }
            )

    per_fold_path = output_dir / f"{output_prefix}_per_fold.csv"
    if per_fold_rows:
        with per_fold_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(per_fold_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_fold_rows)
    paths["per_fold_csv"] = per_fold_path

    predictions_path = output_dir / f"{output_prefix}_predictions.csv"
    if prediction_rows:
        with predictions_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(prediction_rows[0].keys()))
            writer.writeheader()
            writer.writerows(prediction_rows)
    paths["predictions_csv"] = predictions_path

    catboost_result = next(
        (e for e in payload["experiments"] if e["experiment_id"] == "catboost_loto_core7"),
        payload["experiments"][0],
    )
    plots_dir = output_dir / "plots"
    write_loto_plots(payload, plots_dir, catboost_result=catboost_result)
    paths["plots_dir"] = plots_dir

    ds_path = dataset_path or DEFAULT_DATASET_PATH
    if write_results_md and ds_path.exists():
        from match_model.paths import OLD_STATS_DIR
        from match_model.match_vs_market import write_match_vs_market_report

        mvs_path = output_dir / "match_vs_market_report.md"
        if predictions_path.exists():
            write_match_vs_market_report(
                predictions_path=predictions_path,
                dataset_path=ds_path,
                old_stats_dir=OLD_STATS_DIR,
                output_path=mvs_path,
            )
            paths["match_vs_market_md"] = mvs_path

        report_path = write_results_markdown(
            experiments_dir=output_dir,
            dataset_path=ds_path,
            output_path=STAGE_ROOT / "results.md",
            prefix=output_prefix,
        )
        paths["results_md"] = report_path

    return paths
