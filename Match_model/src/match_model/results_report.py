from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from match_model.loto import CATBOOST_EXPERIMENT_ID
from match_model.parsers.old_stats_parser import OldStatsMatch, parse_all_old_stats
from match_model.paths import OLD_STATS_DIR, STAGE_ROOT
from match_model.utils.matching import normalize_team_name, normalized_team_pair


def _pct(x: float) -> str:
    return f"{100.0 * x:.1f}%"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_dataset_rows(dataset_path: Path) -> list[dict[str, Any]]:
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def _load_dataset_index(dataset_path: Path) -> dict[str, dict[str, Any]]:
    rows = _load_dataset_rows(dataset_path)
    return {str(row["match_id"]): row for row in rows}


def _load_old_stats_index(old_stats_dir: Path) -> dict[tuple[str, str, tuple[str, str]], list[OldStatsMatch]]:
    index: dict[tuple[str, str, tuple[str, str]], list[OldStatsMatch]] = defaultdict(list)
    for match in parse_all_old_stats(old_stats_dir):
        pair = normalized_team_pair(match.team1, match.team2)
        index[(match.tournament_id, match.date, pair)].append(match)
    return index


def _per_tournament_table(per_fold_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_comp: dict[str, dict[str, Any]] = {}
    for row in per_fold_rows:
        exp = row["experiment_id"]
        comp = row["held_out_competition"]
        bucket = by_comp.setdefault(
            comp,
            {
                "competition": comp,
                "n_test_matches": int(row["n_test_matches"]),
                "catboost_ce": None,
                "elo_ce": None,
                "catboost_brier": None,
                "elo_brier": None,
            },
        )
        if exp == CATBOOST_EXPERIMENT_ID:
            bucket["catboost_ce"] = float(row["ce"])
            bucket["catboost_brier"] = float(row["brier"])
        elif exp == "baseline__elo":
            bucket["elo_ce"] = float(row["ce"])
            bucket["elo_brier"] = float(row["brier"])

    rows: list[dict[str, Any]] = []
    for comp in sorted(by_comp):
        row = dict(by_comp[comp])
        if row["catboost_ce"] is not None and row["elo_ce"] is not None:
            row["ce_delta_vs_elo"] = row["catboost_ce"] - row["elo_ce"]
        else:
            row["ce_delta_vs_elo"] = None
        if row["catboost_brier"] is not None and row["elo_brier"] is not None:
            row["brier_delta_vs_elo"] = row["catboost_brier"] - row["elo_brier"]
        else:
            row["brier_delta_vs_elo"] = None
        rows.append(row)
    return rows


def _prediction_gap_pp(row: dict[str, str]) -> float:
    return max(
        abs(float(row["pred_a"]) - float(row["target_a"])),
        abs(float(row["pred_draw"]) - float(row["target_draw"])),
        abs(float(row["pred_b"]) - float(row["target_b"])),
    ) * 100.0


def _stage_bucket_table(predictions: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    sums: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"n": 0.0, "ce": 0.0, "brier": 0.0, "mae": 0.0}
    )
    examples: dict[str, dict[str, str]] = {}

    for row in predictions:
        exp = row["experiment_id"]
        if exp not in {CATBOOST_EXPERIMENT_ID, "baseline__elo"}:
            continue
        bucket = "group" if row["stage"] == "group" else "knockout"
        key = (bucket, exp)
        sums[key]["n"] += 1
        sums[key]["ce"] += float(row["ce"])
        sums[key]["brier"] += float(row["brier"])
        sums[key]["mae"] += float(row["mae_macro"])

        if exp == CATBOOST_EXPERIMENT_ID:
            gap_pp = _prediction_gap_pp(row)
            current = examples.get(bucket)
            if current is None or gap_pp > float(current["gap_pp"]):
                examples[bucket] = {
                    "match_id": row["match_id"],
                    "team_a": row["team_a"],
                    "team_b": row["team_b"],
                    "stage": row["stage"],
                    "gap_pp": f"{gap_pp:.1f}",
                    "pred_label": _top_label(float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"])),
                    "pred_prob": _top_prob(float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"])),
                    "target_label": _top_label(
                        float(row["target_a"]),
                        float(row["target_draw"]),
                        float(row["target_b"]),
                    ),
                    "target_prob": _top_prob(
                        float(row["target_a"]),
                        float(row["target_draw"]),
                        float(row["target_b"]),
                    ),
                }

    rows: list[dict[str, Any]] = []
    for bucket in ("group", "knockout"):
        row: dict[str, Any] = {"bucket": bucket, "n": 0}
        for exp, prefix in ((CATBOOST_EXPERIMENT_ID, "catboost"), ("baseline__elo", "elo")):
            stats = sums.get((bucket, exp), {"n": 0.0, "ce": 0.0, "brier": 0.0, "mae": 0.0})
            n = int(stats["n"])
            row["n"] = max(int(row["n"]), n)
            row[f"{prefix}_ce"] = (stats["ce"] / n) if n else None
            row[f"{prefix}_brier"] = (stats["brier"] / n) if n else None
            row[f"{prefix}_mae"] = (stats["mae"] / n) if n else None
        rows.append(row)
    return rows, examples


def _lookup_actual_result(
    match_row: dict[str, Any],
    old_stats_index: dict[tuple[str, str, tuple[str, str]], list[OldStatsMatch]],
) -> dict[str, str]:
    key = (
        str(match_row.get("tournament_id", "")),
        str(match_row.get("date", "")),
        normalized_team_pair(str(match_row.get("team_a", "")), str(match_row.get("team_b", ""))),
    )
    candidates = old_stats_index.get(key, [])
    if not candidates:
        return {"label": "?", "display": "unknown"}

    team_a_norm = normalize_team_name(str(match_row.get("team_a", "")))
    team_b_norm = normalize_team_name(str(match_row.get("team_b", "")))

    for candidate in candidates:
        c1 = normalize_team_name(candidate.team1)
        c2 = normalize_team_name(candidate.team2)
        if (c1, c2) == (team_a_norm, team_b_norm):
            score_a = candidate.score_90_team1
            score_b = candidate.score_90_team2
            break
        if (c1, c2) == (team_b_norm, team_a_norm):
            score_a = candidate.score_90_team2
            score_b = candidate.score_90_team1
            break
    else:
        return {"label": "?", "display": "unknown"}

    team_a = str(match_row.get("team_a", "Team A"))
    team_b = str(match_row.get("team_b", "Team B"))
    if score_a > score_b:
        return {"label": "A", "display": f"{team_a} win ({score_a}-{score_b})"}
    if score_b > score_a:
        return {"label": "B", "display": f"{team_b} win ({score_a}-{score_b})"}
    return {"label": "D", "display": f"Draw ({score_a}-{score_b})"}


def _top_label(p_a: float, p_d: float, p_b: float) -> str:
    scores = [("A", p_a), ("D", p_d), ("B", p_b)]
    return max(scores, key=lambda item: item[1])[0]


def _top_prob(p_a: float, p_d: float, p_b: float) -> float:
    return max(p_a, p_d, p_b)


def _call_name(label: str, team_a: str, team_b: str) -> str:
    if label == "A":
        return team_a
    if label == "B":
        return team_b
    return "Draw"


def _call_text(label: str, prob: float, team_a: str, team_b: str, actual_label: str) -> str:
    status = "hit" if label == actual_label else "miss"
    return f"{_call_name(label, team_a, team_b)} {_pct(prob)} ({status})"


def _brief_reason(row: dict[str, Any]) -> str:
    dataset_row = row.get("dataset_row") or {}
    stage = str(dataset_row.get("stage") or row.get("stage") or "")
    elo = float(dataset_row.get("elo_diff") or row.get("elo_diff") or 0.0)
    target_draw = float(row["target_draw"])
    pred_draw = float(row["pred_draw"])
    target_label = _top_label(float(row["target_a"]), target_draw, float(row["target_b"]))
    pred_label = _top_label(float(row["pred_a"]), pred_draw, float(row["pred_b"]))

    if stage == "group" and target_draw - pred_draw >= 0.08:
        return "The model left too little probability on the draw in a group-stage match."
    if pred_label != target_label:
        return "The model flipped the favorite relative to the market consensus."
    if abs(elo) >= 150:
        return "A large Elo gap appears to have pulled the model too hard toward one side."
    return "The model and market leaned the same way, but the model concentrated too much probability mass."


def _is_large_elo_pattern(row: dict[str, Any]) -> bool:
    return _brief_reason(row) == "A large Elo gap appears to have pulled the model too hard toward one side."


def _worst_predictions(
    predictions: list[dict[str, str]],
    dataset_by_id: dict[str, dict[str, Any]],
    old_stats_index: dict[tuple[str, str, tuple[str, str]], list[OldStatsMatch]],
    *,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in predictions:
        if row["experiment_id"] != CATBOOST_EXPERIMENT_ID:
            continue
        dataset_row = dataset_by_id.get(row["match_id"], {})
        actual = _lookup_actual_result(dataset_row, old_stats_index) if dataset_row else {"label": "?", "display": "unknown"}
        row_copy: dict[str, Any] = dict(row)
        row_copy["ce"] = float(row["ce"])
        row_copy["brier"] = float(row["brier"])
        row_copy["dataset_row"] = dataset_row
        row_copy["actual_result"] = actual
        rows.append(row_copy)
    rows.sort(key=lambda item: item["ce"], reverse=True)
    return rows[:top_n]


def _split_experiments(
    experiments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    predictive = [e for e in experiments if not e.get("is_reference")]
    reference = [e for e in experiments if e.get("is_reference")]
    return predictive, reference


def _macro_mae_pp(
    market_pct: tuple[float, float, float],
    model_pct: tuple[float, float, float],
) -> float:
    return sum(abs(model - market) for market, model in zip(market_pct, model_pct)) / 3.0


def _illustrative_model_line(
    market_pct: tuple[float, float, float],
    target_mae_pp: float,
) -> tuple[float, float, float]:
    """Build a 1X2 line whose macro MAE matches target_mae_pp (favorite softens, draw/away split gain)."""
    favorite, draw, away = market_pct
    shift = target_mae_pp * 0.75  # macro MAE = (2*shift + shift + shift) / 3
    home = round(favorite - 2 * shift, 1)
    draw_out = round(draw + shift, 1)
    away_out = round(100.0 - home - draw_out, 1)
    return home, draw_out, away_out


def _append_1x2_example_table(
    lines: list[str],
    *,
    market_pct: tuple[float, float, float],
    target_mae_pp: float,
) -> float:
    model = _illustrative_model_line(market_pct, target_mae_pp)
    example_mae_pp = _macro_mae_pp(market_pct, model)

    lines.append("| Outcome | Market | Model | Delta pp (model - market) | Abs error |")
    lines.append("|---------|--------|-------|---------------------------|-----------|")
    labels = ("Home win", "Draw", "Away win")
    for label, mkt, mdl in zip(labels, market_pct, model):
        delta = mdl - mkt
        lines.append(
            f"| {label} | {mkt:.1f}% | {mdl:.1f}% | {delta:+.1f} | {abs(delta):.1f} |"
        )
    lines.append(f"| **Macro MAE** | | | | **{example_mae_pp:.2f}** |")
    lines.append("")
    return example_mae_pp


def _append_1x2_error_example_section(lines: list[str], *, mae_macro: float) -> None:
    """Illustrate weighted MAE as typical shifts on one de-vigged 1X2 line."""
    mae_pp = 100.0 * mae_macro
    market = (70.0, 20.0, 10.0)

    lines.append("## 1b. What the errors look like on one 1X2 line")
    lines.append("")
    lines.append(
        "The leaderboard MAE is a macro average over home, draw, and away: for each outcome, take "
        "|model - market|, then average the three. It is **not** the gap on the favorite alone."
    )
    lines.append("")
    lines.append(
        f"CatBoost's weighted MAE is **{mae_pp:.2f} percentage points** per outcome on average "
        f"({mae_macro:.4f} on the 0-1 scale). The table below uses that exact average on one "
        "illustrative de-vigged 1X2 line (favorite probability softens; draw and away share the shift):"
    )
    lines.append("")
    example_mae_pp = _append_1x2_example_table(lines, market_pct=market, target_mae_pp=mae_pp)
    model = _illustrative_model_line(market, mae_pp)
    lines.append(
        f"The favorite is still home, but the model is {abs(model[0] - market[0]):.1f} pp less confident; "
        f"draw and away gain {abs(model[1] - market[1]):.1f} pp and {abs(model[2] - market[2]):.1f} pp. "
        f"Macro MAE on this line is **{example_mae_pp:.2f} pp**, matching the headline **{mae_pp:.2f} pp**."
    )
    lines.append("")
    lines.append(
        "Brier squares those same three gaps before averaging, so it punishes large misses more heavily; "
        "cross-entropy punishes confident wrong calls even more. None of the three numbers is a bracket "
        "probability by itself — they are per-match 1X2 inputs that feed the pairwise simulation stage."
    )
    lines.append("")


def _append_wc2026_1x2_example(lines: list[str], *, mae_macro: float) -> None:
    mae_pp = 100.0 * mae_macro
    market = (58.0, 26.0, 16.0)

    lines.append(
        f"**WC2026 holdout example** (CatBoost weighted MAE **{mae_pp:.2f} pp** on the test set):"
    )
    lines.append("")
    example_mae_pp = _append_1x2_example_table(lines, market_pct=market, target_mae_pp=mae_pp)
    model = _illustrative_model_line(market, mae_pp)
    lines.append(
        f"On a representative group-stage line, home stays the favorite but drops "
        f"{abs(model[0] - market[0]):.1f} pp while draw and away rise "
        f"{abs(model[1] - market[1]):.1f} pp and {abs(model[2] - market[2]):.1f} pp. "
        f"Macro MAE on this line is **{example_mae_pp:.2f} pp**, matching the WC2026 holdout "
        f"**{mae_pp:.2f} pp**."
    )
    lines.append("")


def _load_holdout_payload(experiments_dir: Path) -> dict[str, Any] | None:
    path = experiments_dir / "wc2026_holdout_eval_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _append_ablation_section(
    lines: list[str],
    loto_payload: dict[str, Any],
    holdout_payload: dict[str, Any] | None,
) -> None:
    label_map = {
        CATBOOST_EXPERIMENT_ID: "Base core7",
        "catboost_loto_elo_only": "Elo only",
        "catboost_loto_elo_plus_values": "Elo plus squad values",
        "catboost_loto_minus_values": "Remove squad values",
        "catboost_loto_minus_confed": "Remove confederation",
        "catboost_loto_minus_stage": "Remove stage context",
        "catboost_loto_minus_host": "Remove host advantage",
    }
    ordered_ids = list(label_map)

    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        experiments = {str(exp.get("experiment_id")): exp for exp in payload.get("experiments", [])}
        base = experiments.get(CATBOOST_EXPERIMENT_ID)
        if base is None:
            return []
        base_ce = float(base["summary"]["weighted_ce"])
        base_brier = float(base["summary"]["weighted_brier"])
        rows: list[dict[str, Any]] = []
        for exp_id in ordered_ids:
            exp = experiments.get(exp_id)
            if exp is None:
                continue
            summary = exp["summary"]
            rows.append(
                {
                    "label": label_map[exp_id],
                    "ce": float(summary["weighted_ce"]),
                    "brier": float(summary["weighted_brier"]),
                    "mae": float(summary["weighted_mae_macro"]),
                    "delta_ce": float(summary["weighted_ce"]) - base_ce,
                    "delta_brier": float(summary["weighted_brier"]) - base_brier,
                }
            )
        return rows

    loto_rows = _rows(loto_payload)
    holdout_rows = _rows(holdout_payload or {})
    if not loto_rows:
        return

    lines.append("## 4. Ablation and sensitivity analysis")
    lines.append("")
    lines.append(
        "These fixed ablations test whether the match-level gains depend on a single feature block. "
        "Negative deltas are better for cross-entropy and Brier because the base `core7` model is the reference."
    )
    lines.append("")
    lines.append("### Historical LOTO")
    lines.append("")
    lines.append("| Variant | CE | delta CE vs base | Brier | delta Brier vs base | MAE |")
    lines.append("|---------|----|------------------|-------|---------------------|-----|")
    for row in loto_rows:
        lines.append(
            f"| {row['label']} | {row['ce']:.4f} | {row['delta_ce']:+.4f} | "
            f"{row['brier']:.4f} | {row['delta_brier']:+.4f} | {row['mae']:.4f} |"
        )
    lines.append("")

    if holdout_rows:
        lines.append("### WC2026 holdout")
        lines.append("")
        lines.append("| Variant | CE | delta CE vs base | Brier | delta Brier vs base | MAE |")
        lines.append("|---------|----|------------------|-------|---------------------|-----|")
        for row in holdout_rows:
            lines.append(
                f"| {row['label']} | {row['ce']:.4f} | {row['delta_ce']:+.4f} | "
                f"{row['brier']:.4f} | {row['delta_brier']:+.4f} | {row['mae']:.4f} |"
            )
        lines.append("")

    strongest_drop = max(
        (row for row in loto_rows if row["label"] != "Base core7"),
        key=lambda row: row["delta_ce"],
        default=None,
    )
    if strongest_drop is not None:
        lines.append(
            f"The largest historical degradation comes from **{strongest_drop['label'].lower()}** "
            f"(delta CE {strongest_drop['delta_ce']:+.4f}). This is the quickest read on which block the "
            "base model is leaning on most heavily."
        )
        lines.append("")


def _append_wc2026_holdout_section(
    lines: list[str],
    holdout_payload: dict[str, Any],
    historical_rows: list[dict[str, Any]],
) -> None:
    experiments = holdout_payload.get("experiments", [])
    if not experiments:
        return
    held_out_name = str(holdout_payload.get("held_out_competition") or "World Cup 2026")
    test_dataset_path = holdout_payload.get("test_dataset_path", "unknown")
    lines.append("## 6. WC2026 explicit holdout (train legacy12, test WC2026)")
    lines.append("")
    lines.append(
        f"Train/test split evaluation with train set from legacy12 and held-out test set `{held_out_name}`."
    )
    lines.append(f"WC2026 test dataset: `{test_dataset_path}`")
    lines.append("")
    lines.append("| Experiment | CE | Brier | MAE |")
    lines.append("|------------|----|-------|-----|")
    for exp in experiments:
        summary = exp.get("summary", {})
        lines.append(
            f"| {exp.get('experiment_id')} | {float(summary.get('weighted_ce', 0.0)):.4f} | "
            f"{float(summary.get('weighted_brier', 0.0)):.4f} | {float(summary.get('weighted_mae_macro', 0.0)):.4f} |"
        )
    lines.append("")
    catboost = next((e for e in experiments if e.get("experiment_id") == CATBOOST_EXPERIMENT_ID), None)
    elo = next((e for e in experiments if e.get("experiment_id") == "baseline__elo"), None)
    if catboost and elo:
        cb = float(catboost["summary"]["weighted_ce"])
        el = float(elo["summary"]["weighted_ce"])
        cb_brier = float(catboost["summary"]["weighted_brier"])
        hist_ce = [float(row["catboost_ce"]) for row in historical_rows if row["catboost_ce"] is not None]
        hist_brier = [float(row["catboost_brier"]) for row in historical_rows if row["catboost_brier"] is not None]
        hist_delta = [
            float(row["ce_delta_vs_elo"])
            for row in historical_rows
            if row.get("ce_delta_vs_elo") is not None
        ]
        lines.append(
            f"CatBoost vs Elo on `{held_out_name}` (CE): {cb:.4f} vs {el:.4f} "
            f"(delta {cb - el:+.4f}, negative means CatBoost is better)."
        )
        lines.append("")
        if hist_ce and hist_brier and hist_delta:
            lines.append(
                f"Historical CatBoost ranges across the 12 LOTO folds: CE {min(hist_ce):.4f}-{max(hist_ce):.4f}, "
                f"Brier {min(hist_brier):.4f}-{max(hist_brier):.4f}, and CE delta vs Elo {min(hist_delta):+.4f} to "
                f"{max(hist_delta):+.4f}. The WC2026 holdout lands at CE {cb:.4f}, Brier {cb_brier:.4f}, and "
                f"delta {cb - el:+.4f}."
            )
            lines.append(
                "That does not validate future outcomes, but it does suggest the WC2026 pairwise probability surface "
                "behaves like the historical tournament folds rather than like an obvious outlier, so these "
                "predictions are reasonable inputs for the bracket simulation stage."
            )
            lines.append("")
    if catboost:
        _append_wc2026_1x2_example(
            lines,
            mae_macro=float(catboost["summary"]["weighted_mae_macro"]),
        )


def write_results_markdown(
    *,
    experiments_dir: Path,
    dataset_path: Path,
    output_path: Path | None = None,
    prefix: str = "loto_eval",
) -> Path:
    output_path = output_path or STAGE_ROOT / "results.md"
    experiments_dir = experiments_dir if experiments_dir.is_absolute() else (STAGE_ROOT / experiments_dir)
    dataset_path = dataset_path if dataset_path.is_absolute() else (STAGE_ROOT / dataset_path)
    per_fold_path = experiments_dir / f"{prefix}_per_fold.csv"
    predictions_path = experiments_dir / f"{prefix}_predictions.csv"
    results_path = experiments_dir / f"{prefix}_results.json"

    per_fold_rows = _load_csv_rows(per_fold_path)
    prediction_rows = _load_csv_rows(predictions_path)
    results_payload = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    dataset_by_id = _load_dataset_index(dataset_path)
    tournament_rows = _per_tournament_table(per_fold_rows)
    bucket_rows, bucket_examples = _stage_bucket_table(prediction_rows)
    old_stats_index = _load_old_stats_index(OLD_STATS_DIR)
    worst_rows = _worst_predictions(prediction_rows, dataset_by_id, old_stats_index)
    holdout_payload = _load_holdout_payload(experiments_dir)

    all_experiments = results_payload.get("experiments", [])
    predictive_exps, _ = _split_experiments(all_experiments)
    catboost_exp = next((e for e in predictive_exps if e["experiment_id"] == CATBOOST_EXPERIMENT_ID), None)
    elo_exp = next((e for e in predictive_exps if e.get("baseline_name") == "elo"), None)

    lines: list[str] = []
    lines.append("# Match_model - detailed LOTO results")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Dataset:** `{dataset_path.relative_to(STAGE_ROOT).as_posix()}` ({len(dataset_by_id)} matches)")
    lines.append(f"**Experiments:** `{experiments_dir.relative_to(STAGE_ROOT).as_posix()}`")
    lines.append("")
    lines.append("Standalone stage: inputs under `data/input/legacy12`, stage labels under `data/reference/old_stats`.")
    lines.append("")
    lines.append("## 0. Experiment pipeline")
    lines.append("")
    lines.append(
        "This report summarizes a leave-one-tournament-out workflow over the 12 historical `legacy12` tournaments."
    )
    lines.append(
        "The input dataset is built from committed Elo, confederation, and squad-value features, while the soft label "
        "for each match is the median de-vigged bookmaker consensus over home, draw, and away."
    )
    lines.append(
        "The headline experiment is the seven-feature CatBoost `core7` model, compared against three baselines: "
        "`baseline__elo`, `baseline__marginal`, and the market-structure reference `baseline__market_dispersion`. "
        "A target oracle is also included as a label-plumbing reference rather than a real predictor."
    )
    lines.append("")

    lines.append("## 1. Global leaderboard - predictive models only")
    lines.append("")
    lines.append(
        "Cross-entropy (CE) penalizes assigning low probability to outcomes the market considered likely. "
        "Brier is the squared error across the three 1X2 probabilities. "
        "MAE is the average absolute probability error across the same three outcomes. Lower is better for all three."
    )
    lines.append("")
    lines.append("| Experiment | Weighted CE (lower better) | Weighted Brier | Weighted MAE |")
    lines.append("|------------|----------------------------|----------------|--------------|")
    for exp in predictive_exps:
        summary = exp["summary"]
        lines.append(
            f"| {exp['experiment_id']} | {summary['weighted_ce']:.4f} | {summary['weighted_brier']:.4f} | {summary['weighted_mae_macro']:.4f} |"
        )
    lines.append("")
    if catboost_exp and elo_exp:
        cb_ce = float(catboost_exp["summary"]["weighted_ce"])
        elo_ce = float(elo_exp["summary"]["weighted_ce"])
        lines.append(
            f"**CatBoost vs Elo baseline (weighted CE):** {cb_ce:.4f} vs {elo_ce:.4f} "
            f"(delta = {cb_ce - elo_ce:+.4f}; negative delta means CatBoost is better)."
        )
    lines.append(
        "`baseline__market_dispersion` can score better than CatBoost on CE because it reads market-price "
        "dispersion directly while the target is itself the de-vigged market consensus. Treat it as a "
        "market-aware calibration reference, not a fair standalone predictive baseline; the cleaner "
        "predictive comparison is CatBoost versus `baseline__elo`."
    )
    lines.append("")

    if catboost_exp:
        _append_1x2_error_example_section(
            lines,
            mae_macro=float(catboost_exp["summary"]["weighted_mae_macro"]),
        )

    lines.append("## 2. Per-tournament held-out errors")
    lines.append("")
    lines.append(
        "Each row is one leave-one-tournament-out fold: train on 11 tournaments, test on the held-out competition. "
        "Negative deltas mean CatBoost beat the Elo baseline on that metric."
    )
    lines.append("")
    lines.append(
        "| Tournament | N | CatBoost CE | Elo CE | delta CE vs Elo | CatBoost Brier | Elo Brier | delta Brier vs Elo |"
    )
    lines.append(
        "|------------|---|-------------|--------|-----------------|----------------|-----------|--------------------|"
    )
    for row in tournament_rows:
        ce_delta = row["ce_delta_vs_elo"]
        brier_delta = row["brier_delta_vs_elo"]
        lines.append(
            f"| {row['competition']} | {row['n_test_matches']} | "
            f"{row['catboost_ce']:.4f} | {row['elo_ce']:.4f} | {ce_delta:+.4f} | "
            f"{row['catboost_brier']:.4f} | {row['elo_brier']:.4f} | {brier_delta:+.4f} |"
        )
    if tournament_rows:
        best_ce = min(tournament_rows, key=lambda row: row["ce_delta_vs_elo"])
        worst_ce = max(tournament_rows, key=lambda row: row["ce_delta_vs_elo"])
        best_brier = min(tournament_rows, key=lambda row: row["brier_delta_vs_elo"])
        worst_brier = max(tournament_rows, key=lambda row: row["brier_delta_vs_elo"])
        lines.append("")
        lines.append(f"- **Best CE vs Elo:** {best_ce['competition']} ({best_ce['ce_delta_vs_elo']:+.4f})")
        lines.append(f"- **Worst CE vs Elo:** {worst_ce['competition']} ({worst_ce['ce_delta_vs_elo']:+.4f})")
        lines.append(f"- **Best Brier vs Elo:** {best_brier['competition']} ({best_brier['brier_delta_vs_elo']:+.4f})")
        lines.append(f"- **Worst Brier vs Elo:** {worst_brier['competition']} ({worst_brier['brier_delta_vs_elo']:+.4f})")
        lines.append("")

    lines.append("## 3. Group stage vs knockout matches")
    lines.append("")
    lines.append(
        "The table below splits the held-out match predictions by stage bucket. "
        "This is useful because group matches carry more draw mass, while knockout matches compress the draw problem into a smaller set of usually stronger teams."
    )
    lines.append("")
    lines.append("| Bucket | N | CatBoost CE | Elo CE | CatBoost Brier | Elo Brier | CatBoost MAE | Elo MAE |")
    lines.append("|--------|---|-------------|--------|----------------|-----------|--------------|---------|")
    for row in bucket_rows:
        lines.append(
            f"| {row['bucket']} | {row['n']} | "
            f"{row['catboost_ce']:.4f} | {row['elo_ce']:.4f} | "
            f"{row['catboost_brier']:.4f} | {row['elo_brier']:.4f} | "
            f"{row['catboost_mae']:.4f} | {row['elo_mae']:.4f} |"
        )
    lines.append("")
    for bucket in ("group", "knockout"):
        example = bucket_examples.get(bucket)
        if not example:
            continue
        pred_name = _call_name(example["pred_label"], example["team_a"], example["team_b"])
        target_name = _call_name(example["target_label"], example["team_a"], example["team_b"])
        lines.append(
            f"- **{bucket.title()} large-miss example:** {example['team_a']} vs {example['team_b']} - "
            f"the model's top call was {pred_name} at {_pct(example['pred_prob'])}, while the market target's top call was "
            f"{target_name} at {_pct(example['target_prob'])}; the largest probability miss was {example['gap_pp']} percentage points."
        )
    lines.append("")

    _append_ablation_section(lines, results_payload, holdout_payload)

    lines.append("## 5. Highest cross-entropy predictions (CatBoost)")
    lines.append("")
    lines.append(
        "These are the 10 worst single-match CatBoost CE errors on held-out folds. "
        "The comparison below focuses on the market call, the model call, and the actual 90-minute result from the vendored historical text files."
    )
    lines.append("")
    lines.append("| # | Match | Stage | Actual 90m | Market top call | Model top call | CE | Brier |")
    lines.append("|---|-------|-------|------------|-----------------|----------------|----|-------|")
    for idx, row in enumerate(worst_rows, 1):
        actual = row["actual_result"]
        market_label = _top_label(float(row["target_a"]), float(row["target_draw"]), float(row["target_b"]))
        model_label = _top_label(float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"]))
        market_prob = _top_prob(float(row["target_a"]), float(row["target_draw"]), float(row["target_b"]))
        model_prob = _top_prob(float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"]))
        match_name = f"{row['team_a']} vs {row['team_b']}"
        lines.append(
            f"| {idx} | {match_name} | {row['stage']} | {actual['display']} | "
            f"{_call_text(market_label, market_prob, row['team_a'], row['team_b'], actual['label'])} | "
            f"{_call_text(model_label, model_prob, row['team_a'], row['team_b'], actual['label'])} | "
            f"{row['ce']:.4f} | {row['brier']:.4f} |"
        )
    lines.append("")
    large_elo_rows = [row for row in worst_rows if _is_large_elo_pattern(row)]
    other_rows = [row for row in worst_rows if not _is_large_elo_pattern(row)]
    note_idx = 1
    if large_elo_rows:
        matches = ", ".join(f"{row['team_a']} vs {row['team_b']}" for row in large_elo_rows)
        lines.append(
            f"{note_idx}. **Shared pattern in {len(large_elo_rows)} matches**: {matches}. "
            "In each case, a large Elo gap appears to have pulled the model too hard toward one side."
        )
        note_idx += 1
    for row in other_rows:
        lines.append(
            f"{note_idx}. **{row['team_a']} vs {row['team_b']}**: {_brief_reason(row)}"
        )
        note_idx += 1
    lines.append("")

    if holdout_payload:
        _append_wc2026_holdout_section(lines, holdout_payload, tournament_rows)

    _append_match_vs_market_section(lines, experiments_dir=experiments_dir, dataset_path=dataset_path, prefix=prefix)

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _append_match_vs_market_section(
    lines: list[str],
    *,
    experiments_dir: Path,
    dataset_path: Path,
    prefix: str,
) -> None:
    """Append Section 7: match-level model vs market scored against 90-minute actual outcomes."""
    from match_model.match_vs_market import _agg, compute_match_vs_market
    from match_model.paths import OLD_STATS_DIR

    _WC_TOURNAMENT_IDS = {"world-cup-2010", "world-cup-2014", "world-cup-2018", "world-cup-2022"}
    predictions_path = experiments_dir / f"{prefix}_predictions.csv"
    if not predictions_path.exists() or not dataset_path.exists():
        return

    try:
        matches = compute_match_vs_market(predictions_path, dataset_path, OLD_STATS_DIR)
    except Exception:
        return

    if not matches:
        return

    wc = [m for m in matches if m.get("tournament_id") in _WC_TOURNAMENT_IDS]
    aa = _agg(matches)
    wa = _agg(wc)

    lines.append("## 7. Match-level model vs market — scored against 90-minute actual outcomes")
    lines.append("")
    lines.append(
        "CatBoost LOTO predictions scored against the 90-minute result. "
        "The market predictor is the de-vigged bookmaker consensus (`target_soft`); the model predictor is the "
        "out-of-sample CatBoost `core7` prediction. "
        "Full report: `data/output/experiments/match_vs_market_report.md`."
    )
    lines.append("")
    lines.append(f"### All legacy12 tournaments ({aa['n']} matches)")
    lines.append("")
    lines.append("| Metric | Market | Model |")
    lines.append("|--------|--------|-------|")
    lines.append(
        f"| Log-loss head-to-head wins | **{aa['mkt_ll_wins']} ({aa['mkt_ll_win_pct']:.1%})** "
        f"| {aa['mdl_ll_wins']} ({aa['mdl_ll_win_pct']:.1%}) |"
    )
    lines.append(
        f"| Mean log-loss | **{aa['mean_mkt_ll']:.4f}** "
        f"| {aa['mean_mdl_ll']:.4f} ({aa['mean_mdl_ll'] - aa['mean_mkt_ll']:+.4f}) |"
    )
    lines.append(
        f"| Top-1 accuracy | {aa['mkt_top1']}/{aa['n']} ({aa['mkt_top1_pct']:.1%}) "
        f"| **{aa['mdl_top1']}/{aa['n']} ({aa['mdl_top1_pct']:.1%})** |"
    )
    lines.append("")

    if wa["n"] > 0:
        lines.append(f"### World Cups only — 2010–2022 ({wa['n']} matches)")
        lines.append("")
        lines.append("| Metric | Market | Model |")
        lines.append("|--------|--------|-------|")
        lines.append(
            f"| Log-loss head-to-head wins | **{wa['mkt_ll_wins']} ({wa['mkt_ll_win_pct']:.1%})** "
            f"| {wa['mdl_ll_wins']} ({wa['mdl_ll_win_pct']:.1%}) |"
        )
        lines.append(
            f"| Mean log-loss | **{wa['mean_mkt_ll']:.4f}** "
            f"| {wa['mean_mdl_ll']:.4f} ({wa['mean_mdl_ll'] - wa['mean_mkt_ll']:+.4f}) |"
        )
        lines.append(
            f"| Top-1 accuracy | {wa['mkt_top1']}/{wa['n']} ({wa['mkt_top1_pct']:.1%}) "
            f"| **{wa['mdl_top1']}/{wa['n']} ({wa['mdl_top1_pct']:.1%})** |"
        )
        lines.append("")
        extra = wa["mdl_top1"] - wa["mkt_top1"]
        sign = "+" if extra >= 0 else ""
        lines.append(
            f"The market wins slightly more per-game log-loss comparisons. "
            f"The model has a {sign}{extra} top-1 edge on World Cup matches "
            f"({wa['mdl_top1']} vs {wa['mkt_top1']}), picking the right favourite more often "
            "even while trailing on mean log-loss (it is more confident on some wrong calls)."
        )
        lines.append("")
