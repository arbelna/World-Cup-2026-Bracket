"""
Match-level model vs market accuracy against 90-minute actual outcomes.

Generates the Section 7 analysis from results.md: per-match log-loss, Brier,
and top-1 comparisons between the CatBoost LOTO predictions and the de-vigged
market consensus, scored against the committed old_stats actual results.

Run via:
    python main_cli.py match-vs-market
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from match_model.loto import CATBOOST_EXPERIMENT_ID
from match_model.results_report import (
    _load_csv_rows,
    _load_dataset_index,
    _load_old_stats_index,
    _lookup_actual_result,
    _top_label,
)


# ---------------------------------------------------------------------------
# Per-match computation helpers
# ---------------------------------------------------------------------------

def _log_loss(p_actual: float) -> float:
    return -math.log(max(p_actual, 1e-15))


def _brier_3class(probs: tuple[float, float, float], actual: str) -> float:
    labels = ("A", "D", "B")
    return sum(
        (p - (1.0 if label == actual else 0.0)) ** 2
        for p, label in zip(probs, labels)
    )


def _agg(matches: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(matches)
    if n == 0:
        return {"n": 0}
    mkt_ll_wins = sum(1 for m in matches if m["mkt_ll"] < m["mdl_ll"])
    mdl_ll_wins = sum(1 for m in matches if m["mdl_ll"] < m["mkt_ll"])
    return {
        "n": n,
        "mkt_ll_wins": mkt_ll_wins,
        "mdl_ll_wins": mdl_ll_wins,
        "mkt_ll_win_pct": mkt_ll_wins / n,
        "mdl_ll_win_pct": mdl_ll_wins / n,
        "mean_mkt_ll": sum(m["mkt_ll"] for m in matches) / n,
        "mean_mdl_ll": sum(m["mdl_ll"] for m in matches) / n,
        "mean_mkt_brier": sum(m["mkt_brier"] for m in matches) / n,
        "mean_mdl_brier": sum(m["mdl_brier"] for m in matches) / n,
        "mkt_top1": sum(1 for m in matches if m["mkt_top1"]),
        "mdl_top1": sum(1 for m in matches if m["mdl_top1"]),
        "mkt_top1_pct": sum(1 for m in matches if m["mkt_top1"]) / n,
        "mdl_top1_pct": sum(1 for m in matches if m["mdl_top1"]) / n,
        "elo_top1": sum(1 for m in matches if m.get("elo_top1")),
        "mean_elo_ll": (
            sum(m["elo_ll"] for m in matches if m.get("elo_ll") is not None)
            / max(1, sum(1 for m in matches if m.get("elo_ll") is not None))
        ),
        "elo_ll_wins_vs_mkt": sum(
            1 for m in matches
            if m.get("elo_ll") is not None and m["elo_ll"] < m["mkt_ll"]
        ),
    }


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

_WC_TOURNAMENT_IDS = {"world-cup-2010", "world-cup-2014", "world-cup-2018", "world-cup-2022"}


def compute_match_vs_market(
    predictions_path: Path,
    dataset_path: Path,
    old_stats_dir: Path,
) -> list[dict[str, Any]]:
    """
    Return one record per scored match with log-loss/Brier/top-1 for market,
    model (CatBoost), and Elo baseline, each scored against the 90-minute result.
    """
    prediction_rows = _load_csv_rows(predictions_path)
    dataset_by_id = _load_dataset_index(dataset_path)
    old_stats_index = _load_old_stats_index(old_stats_dir)

    # Group rows by match_id
    by_match: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in prediction_rows:
        by_match[row["match_id"]][row["experiment_id"]] = row

    records: list[dict[str, Any]] = []
    for match_id, exp_rows in by_match.items():
        cb_row = exp_rows.get(CATBOOST_EXPERIMENT_ID)
        if cb_row is None:
            continue
        dataset_row = dataset_by_id.get(match_id, {})
        actual = _lookup_actual_result(dataset_row, old_stats_index)
        if actual["label"] == "?":
            continue

        label = actual["label"]  # "A", "D", or "B"
        label_idx = {"A": 0, "D": 1, "B": 2}[label]

        mkt_probs: tuple[float, float, float] = (
            float(cb_row["target_a"]),
            float(cb_row["target_draw"]),
            float(cb_row["target_b"]),
        )
        mdl_probs: tuple[float, float, float] = (
            float(cb_row["pred_a"]),
            float(cb_row["pred_draw"]),
            float(cb_row["pred_b"]),
        )
        elo_row = exp_rows.get("baseline__elo")
        elo_probs: tuple[float, float, float] | None = (
            (float(elo_row["pred_a"]), float(elo_row["pred_draw"]), float(elo_row["pred_b"]))
            if elo_row else None
        )

        records.append({
            "match_id": match_id,
            "competition": str(dataset_row.get("competition", "")),
            "tournament_id": str(dataset_row.get("tournament_id", "")),
            "stage": str(dataset_row.get("stage", "")),
            "team_a": str(dataset_row.get("team_a", cb_row.get("team_a", ""))),
            "team_b": str(dataset_row.get("team_b", cb_row.get("team_b", ""))),
            "actual": label,
            "mkt_ll": _log_loss(mkt_probs[label_idx]),
            "mdl_ll": _log_loss(mdl_probs[label_idx]),
            "elo_ll": _log_loss(elo_probs[label_idx]) if elo_probs else None,
            "mkt_brier": _brier_3class(mkt_probs, label),
            "mdl_brier": _brier_3class(mdl_probs, label),
            "mkt_top1": _top_label(*mkt_probs) == label,
            "mdl_top1": _top_label(*mdl_probs) == label,
            "elo_top1": (_top_label(*elo_probs) == label) if elo_probs else None,
            "same_fav": _top_label(*mkt_probs) == _top_label(*mdl_probs),
        })

    return records


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------

def write_match_vs_market_report(
    *,
    predictions_path: Path,
    dataset_path: Path,
    old_stats_dir: Path,
    output_path: Path,
) -> Path:
    """Compute and write the full Section 7 markdown report."""
    matches = compute_match_vs_market(predictions_path, dataset_path, old_stats_dir)
    wc = [m for m in matches if m["tournament_id"] in _WC_TOURNAMENT_IDS]

    lines: list[str] = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines += [
        "# Match-level model vs market vs actual outcomes",
        "",
        f"**Generated:** {ts}",
        f"**Scope:** {len(matches)} LOTO CatBoost predictions scored against 90-minute actual results.",
        "",
        "For each match the market probability is the de-vigged bookmaker consensus (`target_soft`). "
        "The model probability is the CatBoost `core7` LOTO out-of-sample prediction. "
        "Knockout matches that went to extra time or penalties are scored on the 90-minute result.",
        "",
    ]

    # --- all tournaments ---
    aa = _agg(matches)
    lines += [
        "## All legacy12 tournaments",
        "",
        "| Metric | Market | Model |",
        "|--------|--------|-------|",
        f"| Log-loss head-to-head wins | **{aa['mkt_ll_wins']} ({aa['mkt_ll_win_pct']:.1%})** | {aa['mdl_ll_wins']} ({aa['mdl_ll_win_pct']:.1%}) |",
        f"| Mean log-loss | **{aa['mean_mkt_ll']:.4f}** | {aa['mean_mdl_ll']:.4f} ({aa['mean_mdl_ll'] - aa['mean_mkt_ll']:+.4f}) |",
        f"| Mean 3-class Brier vs actuals | **{aa['mean_mkt_brier']:.4f}** | {aa['mean_mdl_brier']:.4f} ({aa['mean_mdl_brier'] - aa['mean_mkt_brier']:+.4f}) |",
        f"| Top-1 accuracy | {aa['mkt_top1']}/{aa['n']} ({aa['mkt_top1_pct']:.1%}) | **{aa['mdl_top1']}/{aa['n']} ({aa['mdl_top1_pct']:.1%})** |",
        "",
    ]

    # --- World Cups only ---
    wa = _agg(wc)
    lines += [
        "## World Cups only — 2010–2022",
        "",
        "| Metric | Market | Model |",
        "|--------|--------|-------|",
        f"| Log-loss head-to-head wins | **{wa['mkt_ll_wins']} ({wa['mkt_ll_win_pct']:.1%})** | {wa['mdl_ll_wins']} ({wa['mdl_ll_win_pct']:.1%}) |",
        f"| Mean log-loss | **{wa['mean_mkt_ll']:.4f}** | {wa['mean_mdl_ll']:.4f} ({wa['mean_mdl_ll'] - wa['mean_mkt_ll']:+.4f}) |",
        f"| Mean 3-class Brier vs actuals | **{wa['mean_mkt_brier']:.4f}** | {wa['mean_mdl_brier']:.4f} ({wa['mean_mdl_brier'] - wa['mean_mkt_brier']:+.4f}) |",
        f"| Top-1 accuracy | {wa['mkt_top1']}/{wa['n']} ({wa['mkt_top1_pct']:.1%}) | **{wa['mdl_top1']}/{wa['n']} ({wa['mdl_top1_pct']:.1%})** |",
        "",
        "The market wins slightly more than half of per-game log-loss comparisons. The model has a small "
        "edge on top-1 pick rate but loses on mean log-loss because it is often **more confident on wrong calls**.",
        "",
        "> **Note:** Brier values here (~0.57) are computed against hard one-hot actual outcomes and are not "
        "comparable to the soft-label Brier (~0.008) in the LOTO leaderboard, which measures distance from "
        "the market consensus.",
        "",
    ]

    # --- by stage ---
    lines += ["## By stage (World Cups)", ""]
    lines += [
        "| Stage | N | Model LL wins | Market LL wins | Mean Δ log-loss (model − market) |",
        "|-------|---|---------------|----------------|----------------------------------|",
    ]
    for bucket in ("group", "knockout"):
        bm = [m for m in wc if ("group" in m["stage"]) == (bucket == "group")]
        if not bm:
            continue
        ba = _agg(bm)
        delta = ba["mean_mdl_ll"] - ba["mean_mkt_ll"]
        lines.append(
            f"| {bucket.capitalize()} | {ba['n']} | {ba['mdl_ll_wins']} ({ba['mdl_ll_win_pct']:.1%}) "
            f"| {ba['mkt_ll_wins']} ({ba['mkt_ll_win_pct']:.1%}) | {delta:+.4f} |"
        )
    lines.append("")
    lines += [
        "| Stage | Market top-1 | Model top-1 |",
        "|-------|--------------|-------------|",
    ]
    for bucket in ("group", "knockout"):
        bm = [m for m in wc if ("group" in m["stage"]) == (bucket == "group")]
        if not bm:
            continue
        ba = _agg(bm)
        lines.append(
            f"| {bucket.capitalize()} | {ba['mkt_top1']}/{ba['n']} ({ba['mkt_top1_pct']:.1%}) "
            f"| {ba['mdl_top1']}/{ba['n']} ({ba['mdl_top1_pct']:.1%}) |"
        )
    lines.append("")

    # --- top-1 breakdown ---
    both_ok = sum(1 for m in wc if m["mkt_top1"] and m["mdl_top1"])
    mkt_only = sum(1 for m in wc if m["mkt_top1"] and not m["mdl_top1"])
    mdl_only = sum(1 for m in wc if m["mdl_top1"] and not m["mkt_top1"])
    neither = sum(1 for m in wc if not m["mkt_top1"] and not m["mdl_top1"])
    extra = wa["mdl_top1"] - wa["mkt_top1"]
    lines += [
        "## Top-1 breakdown (World Cups)",
        "",
        "| Category | Count |",
        "|----------|-------|",
        f"| Both market and model pick correctly | {both_ok} |",
        f"| Market only correct | {mkt_only} |",
        f"| Model only correct | {mdl_only} |",
        f"| Neither correct | {neither} |",
        "",
        f"The model earns **{abs(extra)} extra correct top-1 picks** ({wa['mdl_top1']} vs {wa['mkt_top1']}) "
        "but loses the log-loss tally because wrong predictions tend to carry higher misplaced confidence.",
        "",
    ]

    # --- when they disagree ---
    disagree = [m for m in wc if not m["same_fav"]]
    if disagree:
        da = _agg(disagree)
        lines += [
            f"When model and market disagree on the favourite ({len(disagree)} games): "
            f"log-loss essentially even (model {da['mdl_ll_wins']}, market {da['mkt_ll_wins']} wins); "
            f"model top-1 edge {da['mdl_top1']} vs {da['mkt_top1']}.",
            "",
        ]

    # --- per World Cup ---
    lines += [
        "## Per World Cup",
        "",
        "| Tournament | N | Model LL wins | Market LL wins | Mean Δ log-loss | Top-1 market / model |",
        "|------------|---|---------------|----------------|-----------------|----------------------|",
    ]
    for tid in sorted(_WC_TOURNAMENT_IDS):
        tm = [m for m in wc if m["tournament_id"] == tid]
        if not tm:
            continue
        ta = _agg(tm)
        delta = ta["mean_mdl_ll"] - ta["mean_mkt_ll"]
        comp = tm[0]["competition"]
        lines.append(
            f"| {comp} | {ta['n']} | {ta['mdl_ll_wins']} | {ta['mkt_ll_wins']} "
            f"| {delta:+.4f} | {ta['mkt_top1']} / {ta['mdl_top1']} |"
        )
    lines.append("")

    # --- Elo comparison ---
    elo_wc = [m for m in wc if m.get("elo_ll") is not None]
    if elo_wc:
        ea = _agg(elo_wc)
        n = len(elo_wc)
        mdl_wins_vs_mkt = sum(1 for m in elo_wc if m["mdl_ll"] < m["mkt_ll"])
        lines += [
            "## Elo vs CatBoost vs market (World Cups)",
            "",
            "| Predictor | Beats market (log-loss) | Mean log-loss | Top-1 correct |",
            "|-----------|-------------------------|---------------|---------------|",
            f"| **Market** | — | **{ea['mean_mkt_ll']:.4f}** | {ea['mkt_top1']}/{n} |",
            f"| **CatBoost** | {mdl_wins_vs_mkt}/{n} ({mdl_wins_vs_mkt/n:.1%}) | {ea['mean_mdl_ll']:.4f} | **{ea['mdl_top1']}/{n}** |",
            f"| **Elo** | {ea['elo_ll_wins_vs_mkt']}/{n} ({ea['elo_ll_wins_vs_mkt']/n:.1%}) | {ea['mean_elo_ll']:.4f} | {ea['elo_top1']}/{n} |",
            "",
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
