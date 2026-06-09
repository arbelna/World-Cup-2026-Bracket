from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bracket_simulations.actual_results import EXPECTED_N, STAGES, build_actual_outcome
from bracket_simulations.aggregates import resolve_bracket_output_dir, settings_fingerprint
from bracket_simulations.compare import _load_preds, evaluate_marginal, probabilities_csv
from bracket_simulations.config import load_tournament_config
from bracket_simulations.model_variants import MODEL_VARIANTS, resolve_model_variant
from bracket_simulations.pairwise.precompute import precompute_for_config
from bracket_simulations.paths import DATA_OUTPUT
from bracket_simulations.run import run_simulations
from bracket_simulations.simulator.bracket_resolver import load_groups

ROBUSTNESS_VARIANT_IDS: tuple[str, ...] = (
    "base",
    "elo_only",
    "elo_plus_values",
    "minus_confed",
    "host_off",
    "stage_neutral",
)
SEED_SENSITIVITY_SEEDS: tuple[int, ...] = (42, 43, 44)
ALPHA_KNOCKOUT_VALUES: tuple[float, ...] = (0.25, 0.50, 0.75)
ROBUSTNESS_JSON_PATH = DATA_OUTPUT / "stage_prediction_robustness.json"
ROBUSTNESS_METRICS: tuple[str, ...] = (
    "m1_recall_model",
    "m2_brier_qualifiers_model",
    "m5_brier_model",
    "m6_logloss_model",
)


def _stage_metrics(
    *,
    tournament: str,
    mode: str,
    alphas: dict[str, float] | None = None,
    tag: str | None = None,
) -> dict[str, dict[str, float]]:
    cfg = load_tournament_config(tournament)
    groups = load_groups(cfg.groups_file)
    all_teams = sorted({team for teams in groups.values() for team in teams})
    actual = build_actual_outcome(tournament)

    market_preds = _load_preds(probabilities_csv(tournament, "market_all"))
    model_preds = _load_preds(probabilities_csv(tournament, mode, alphas=alphas, tag=tag))
    market_sum = evaluate_marginal(market_preds, all_teams, actual.actual_at_least)
    model_sum = evaluate_marginal(model_preds, all_teams, actual.actual_at_least)

    out: dict[str, dict[str, float]] = {}
    for stage in STAGES:
        n = EXPECTED_N[stage]
        m1_market = market_sum[stage]["topn_hits"] / n
        m1_model = model_sum[stage]["topn_hits"] / n
        m2_market = float(market_sum[stage]["brier_qualifiers"])
        m2_model = float(model_sum[stage]["brier_qualifiers"])
        m5_market = float(market_sum[stage]["brier"])
        m5_model = float(model_sum[stage]["brier"])
        m6_market = float(market_sum[stage]["logloss"])
        m6_model = float(model_sum[stage]["logloss"])
        out[stage] = {
            "m1_recall_market": m1_market,
            "m1_recall_model": m1_model,
            "m1_delta_vs_market": m1_model - m1_market,
            "m2_brier_qualifiers_market": m2_market,
            "m2_brier_qualifiers_model": m2_model,
            "m2_delta_vs_market": m2_model - m2_market,
            "m5_brier_market": m5_market,
            "m5_brier_model": m5_model,
            "m5_delta_vs_market": m5_model - m5_market,
            "m6_logloss_market": m6_market,
            "m6_logloss_model": m6_model,
            "m6_delta_vs_market": m6_model - m6_market,
        }
    return out


def _aggregate_stage_metrics(
    by_tournament: dict[str, dict[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    tournaments = list(by_tournament)
    aggregate: dict[str, dict[str, float]] = {}
    for stage in STAGES:
        stage_values = [by_tournament[t][stage] for t in tournaments]
        keys = stage_values[0].keys()
        aggregate[stage] = {
            key: sum(float(values[key]) for values in stage_values) / len(stage_values)
            for key in keys
        }
    return aggregate


def _claim_flags(aggregate: dict[str, dict[str, float]]) -> dict[str, Any]:
    m1_model_better = sum(1 for stage in STAGES if aggregate[stage]["m1_delta_vs_market"] > 0.0)
    m2_market_better = sum(1 for stage in STAGES if aggregate[stage]["m2_delta_vs_market"] > 0.0)
    m5_market_better = sum(1 for stage in STAGES if aggregate[stage]["m5_delta_vs_market"] > 0.0)
    m6_market_better = sum(1 for stage in STAGES if aggregate[stage]["m6_delta_vs_market"] > 0.0)
    return {
        "m1_model_better_stages": m1_model_better,
        "m2_market_better_stages": m2_market_better,
        "m5_market_better_stages": m5_market_better,
        "m6_market_better_stages": m6_market_better,
        "holds_base_claims": (
            m1_model_better == len(STAGES)
            and m2_market_better == len(STAGES)
            and m5_market_better == len(STAGES)
            and m6_market_better == len(STAGES)
        ),
    }


def summarize_mode_metrics(
    tournaments: list[str],
    *,
    mode: str,
    alphas: dict[str, float] | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    by_tournament = {
        tournament: _stage_metrics(tournament=tournament, mode=mode, alphas=alphas, tag=tag)
        for tournament in tournaments
    }
    aggregate = _aggregate_stage_metrics(by_tournament)
    return {
        "mode": mode,
        "tag": tag,
        "alphas": alphas,
        "by_tournament": by_tournament,
        "aggregate": aggregate,
        "claims": _claim_flags(aggregate),
    }


def _sequence_summary(
    summaries: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for stage in STAGES:
        out[stage] = {}
        for metric in ROBUSTNESS_METRICS:
            values = {label: float(summary["aggregate"][stage][metric]) for label, summary in summaries.items()}
            mean_value = sum(values.values()) / len(values)
            min_value = min(values.values())
            max_value = max(values.values())
            out[stage][metric] = {
                "mean": mean_value,
                "min": min_value,
                "max": max_value,
                "range": max_value - min_value,
                "max_abs_deviation": max(abs(value - mean_value) for value in values.values()),
                "values": values,
            }
    return out


def _delta_vs_base(
    base_summary: dict[str, Any],
    variant_summary: dict[str, Any],
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for stage in STAGES:
        out[stage] = {}
        for metric in ROBUSTNESS_METRICS:
            out[stage][metric] = (
                float(variant_summary["aggregate"][stage][metric])
                - float(base_summary["aggregate"][stage][metric])
            )
    return out


def _alpha_alphas(cfg_alphas: dict[str, float], alpha_knockout: float) -> dict[str, float]:
    alphas = dict(cfg_alphas)
    for stage in ("R16", "QF", "SF", "final", "third_place", "R32"):
        if stage in alphas:
            alphas[stage] = alpha_knockout
    return alphas


def _run_sim(
    *,
    tournament: str,
    mode: str,
    n_sims: int,
    batch_size: int,
    seed: int,
    reset: bool,
    verbose: bool,
    alpha_knockout: float | None = None,
    settings_tag: str | None = None,
) -> None:
    args = argparse.Namespace(
        tournament=tournament,
        mode=mode,
        n_sims=n_sims,
        batch_size=batch_size,
        seed=seed,
        alpha_knockout=alpha_knockout,
        alpha_group_tie=None,
        settings_tag=settings_tag,
        reset=reset,
        force_reset=False,
        verbose=verbose,
        stop_after_group=False,
    )
    run_simulations(args)


def _maybe_precompute_variant(tournaments: list[str], variant_id: str) -> None:
    for tournament in tournaments:
        precompute_for_config(tournament, variant_id=variant_id)


def build_robustness_payload(
    tournaments: list[str],
    *,
    n_sims: int,
    batch_size: int,
    reset: bool,
    verbose: bool,
) -> dict[str, Any]:
    for variant_id in ROBUSTNESS_VARIANT_IDS:
        _maybe_precompute_variant(tournaments, variant_id)

    variant_runs: dict[str, dict[str, Any]] = {}
    for variant_id in ROBUSTNESS_VARIANT_IDS:
        variant = resolve_model_variant(variant_id=variant_id)
        tag = f"robust_variant_{variant.variant_id}"
        for tournament in tournaments:
            _run_sim(
                tournament=tournament,
                mode=variant.mode_name,
                n_sims=n_sims,
                batch_size=batch_size,
                seed=42,
                reset=reset,
                verbose=verbose,
                settings_tag=tag,
            )
        variant_runs[variant.variant_id] = summarize_mode_metrics(
            tournaments,
            mode=variant.mode_name,
            tag=tag,
        )
        variant_runs[variant.variant_id]["label"] = variant.label

    seed_runs: dict[str, dict[str, Any]] = {}
    for seed in SEED_SENSITIVITY_SEEDS:
        tag = f"robust_seed_{seed}"
        for tournament in tournaments:
            _run_sim(
                tournament=tournament,
                mode="model_all",
                n_sims=n_sims,
                batch_size=batch_size,
                seed=seed,
                reset=reset,
                verbose=verbose,
                settings_tag=tag,
            )
        seed_runs[str(seed)] = summarize_mode_metrics(
            tournaments,
            mode="model_all",
            tag=tag,
        )

    alpha_runs: dict[str, dict[str, Any]] = {}
    base_cfg = load_tournament_config(tournaments[0])
    for alpha in ALPHA_KNOCKOUT_VALUES:
        tag = f"robust_alpha_{alpha:.2f}"
        for tournament in tournaments:
            _run_sim(
                tournament=tournament,
                mode="model_all",
                n_sims=n_sims,
                batch_size=batch_size,
                seed=42,
                reset=reset,
                verbose=verbose,
                alpha_knockout=alpha,
                settings_tag=tag,
            )
        alpha_runs[f"{alpha:.2f}"] = summarize_mode_metrics(
            tournaments,
            mode="model_all",
            alphas=_alpha_alphas(base_cfg.alphas, alpha),
            tag=tag,
        )

    base_variant_summary = variant_runs["base"]
    payload = {
        "tournaments": tournaments,
        "n_sims": n_sims,
        "batch_size": batch_size,
        "variants": {
            variant_id: {
                **summary,
                "delta_vs_base": _delta_vs_base(base_variant_summary, summary),
            }
            for variant_id, summary in variant_runs.items()
        },
        "seed_sensitivity": {
            "seeds": list(SEED_SENSITIVITY_SEEDS),
            "runs": seed_runs,
            "summary": _sequence_summary(seed_runs),
        },
        "alpha_sensitivity": {
            "alpha_knockout_values": [f"{alpha:.2f}" for alpha in ALPHA_KNOCKOUT_VALUES],
            "runs": alpha_runs,
            "summary": _sequence_summary(alpha_runs),
            "delta_vs_base": {
                alpha_key: _delta_vs_base(base_variant_summary, summary)
                for alpha_key, summary in alpha_runs.items()
            },
        },
    }
    return payload


def write_robustness_payload(payload: dict[str, Any], path: Path | None = None) -> Path:
    out_path = path or ROBUSTNESS_JSON_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def load_robustness_payload(path: Path | None = None) -> dict[str, Any] | None:
    target = path or ROBUSTNESS_JSON_PATH
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))
