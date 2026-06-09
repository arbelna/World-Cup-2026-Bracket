from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from bracket_simulations.actual_results import STAGES, EXPECTED_N, build_actual_outcome
from bracket_simulations.aggregates import (
    config_probability,
    config_rank,
    load_state,
    resolve_bracket_output_dir,
    settings_fingerprint,
    top_config_for_stage,
)
from bracket_simulations.config import load_tournament_config, list_tournament_config_names
from bracket_simulations.paths import DATA_OUTPUT, STAGE_ROOT
from bracket_simulations.simulator.bracket_resolver import load_groups

TOURNAMENTS = list_tournament_config_names()
MODES = ("market_all", "model_all")


def _load_preds(path: Path) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["team"]] = {k: float(row[k]) for k in row if k.startswith("p_")}
    return rows


def probabilities_csv(
    tournament: str,
    mode: str,
    *,
    alphas: dict[str, float] | None = None,
    tag: str | None = None,
) -> Path:
    cfg = load_tournament_config(tournament)
    fp = settings_fingerprint(
        tournament=tournament,
        mode=mode,
        alphas=dict(alphas or cfg.alphas),
        tag=tag,
    )
    path = resolve_bracket_output_dir(cfg.output_dir, mode=mode, settings_fp=fp) / "team_stage_probabilities.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run simulate for {tournament} mode={mode} first."
        )
    return path


def state_json(
    tournament: str,
    mode: str,
    *,
    alphas: dict[str, float] | None = None,
    tag: str | None = None,
) -> Path:
    cfg = load_tournament_config(tournament)
    fp = settings_fingerprint(
        tournament=tournament,
        mode=mode,
        alphas=dict(alphas or cfg.alphas),
        tag=tag,
    )
    return resolve_bracket_output_dir(cfg.output_dir, mode=mode, settings_fp=fp) / "state.json"


def evaluate_marginal(
    preds: dict[str, dict[str, float]],
    all_teams: list[str],
    actual_at_least: dict[str, set[str]],
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for stage in STAGES:
        col = f"p_at_least_{stage}"
        actual_set = actual_at_least[stage]
        n = EXPECTED_N[stage]
        correct_05 = 0
        brier = 0.0
        logloss = 0.0
        for team in all_teams:
            p = preds[team][col]
            y = 1 if team in actual_set else 0
            if (1 if p >= 0.5 else 0) == y:
                correct_05 += 1
            brier += (p - y) ** 2
            p_clip = min(max(p, 1e-15), 1 - 1e-15)
            logloss += -(y * math.log(p_clip) + (1 - y) * math.log(1 - p_clip))
        brier_qualifiers = sum((preds[t][col] - 1.0) ** 2 for t in actual_set) / len(actual_set)
        ranked = sorted(all_teams, key=lambda t: preds[t][col], reverse=True)
        topn = set(ranked[:n])
        summary[stage] = {
            "correct_05": correct_05,
            "brier": brier / len(all_teams),
            "brier_qualifiers": brier_qualifiers,
            "logloss": logloss / len(all_teams),
            "topn_hits": len(topn & actual_set),
            "topn_fp": len(topn - actual_set),
        }
    return summary


def evaluate_joint(state: dict[str, Any], actual_config: dict[str, tuple[str, ...]]) -> dict[str, dict[str, float | bool | int]]:
    summary: dict[str, dict[str, float | bool | int]] = {}
    for stage in STAGES:
        actual = tuple(sorted(actual_config[stage]))
        p_actual = config_probability(state, stage, actual)
        top = top_config_for_stage(state, stage)
        top1_correct = top is not None and top[0] == actual
        n_unique = sum(1 for k in state.get("config_counts", {}) if k.startswith(stage + "|||"))
        summary[stage] = {
            "p_joint_actual": p_actual,
            "neg_log_p_actual": -math.log(max(p_actual, 1e-15)),
            "rank_actual": config_rank(state, stage, actual),
            "top1_correct": top1_correct,
            "n_unique_configs": n_unique,
            "top1_probability": top[1] if top else 0.0,
        }
        if top:
            summary[stage]["top1_teams"] = "|".join(top[0])
    return summary


def compare_tournament(tournament: str) -> dict[str, Any]:
    cfg = load_tournament_config(tournament)
    groups = load_groups(cfg.groups_file)
    all_teams = sorted({t for ts in groups.values() for t in ts})
    actual = build_actual_outcome(tournament)

    result: dict[str, Any] = {
        "tournament": tournament,
        "competition": cfg.match_dataset_filter_competition,
        "champion_actual": actual.champion,
        "actual_config": {k: list(v) for k, v in actual.actual_config.items()},
    }

    for mode in MODES:
        preds = _load_preds(probabilities_csv(tournament, mode))
        state = load_state(state_json(tournament, mode))
        marginal = evaluate_marginal(preds, all_teams, actual.actual_at_least)
        joint = evaluate_joint(state, actual.actual_config)
        winner_col = "p_at_least_winner"
        top_pick = max(all_teams, key=lambda t: preds[t][winner_col])
        result[mode] = {
            "marginal": marginal,
            "joint": joint,
            "champion_pick": top_pick,
            "p_winner_actual": preds[actual.champion][winner_col],
        }
    return result


def compare_tournament_market_reference(tournament: str) -> dict[str, Any]:
    cfg = load_tournament_config(tournament)
    groups = load_groups(cfg.groups_file)
    all_teams = sorted({t for ts in groups.values() for t in ts})
    market = _load_preds(probabilities_csv(tournament, "market_all"))
    model = _load_preds(probabilities_csv(tournament, "model_all"))

    stages: list[str] = []
    if cfg.has_r32:
        stages = ["R32"]
    else:
        stages = [s for s in STAGES if f"p_at_least_{s}" in next(iter(market.values()), {})]

    stage_metrics: dict[str, dict[str, float]] = {}
    for stage in stages:
        col = f"p_at_least_{stage}"
        diffs = [model[t][col] - market[t][col] for t in all_teams if t in market and t in model]
        if not diffs:
            continue
        mse = sum(d * d for d in diffs) / len(diffs)
        mae = sum(abs(d) for d in diffs) / len(diffs)
        stage_metrics[stage] = {"mse_model_vs_market": mse, "mae_model_vs_market": mae}

    return {
        "tournament": tournament,
        "competition": cfg.match_dataset_filter_competition,
        "comparison_mode": "market_reference",
        "stages_compared": stages,
        "market_reference": stage_metrics,
    }


def run_compare(*, json_out: Path | None = None) -> list[dict[str, Any]]:
    results = []
    for tournament in TOURNAMENTS:
        try:
            results.append(compare_tournament(tournament))
        except (ValueError, KeyError):
            results.append(compare_tournament_market_reference(tournament))
        except FileNotFoundError as exc:
            results.append({"tournament": tournament, "error": str(exc)})
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    from bracket_simulations.results_report import write_results_md

    brier_path = STAGE_ROOT / "data" / "output" / "compare_brier_summary.md"
    write_results_md(results, brier_path)
    return results
