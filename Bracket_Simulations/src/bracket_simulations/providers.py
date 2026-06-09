from __future__ import annotations

from bracket_simulations.config import TournamentConfig
from bracket_simulations.model_variants import resolve_model_variant, variant_pairwise_path
from bracket_simulations.probabilities.market import MarketProbabilityProvider
from bracket_simulations.probabilities.market_knockout import MarketKnockoutProbabilityProvider
from bracket_simulations.probabilities.model import (
    ModelGroupProbabilityProvider,
    ModelKnockoutProbabilityProvider,
)


def resolve_prob_providers(cfg: TournamentConfig, mode: str, groups: dict[str, list[str]]):
    if mode == "market_all":
        group_market = MarketProbabilityProvider.for_tournament_market_all_group(cfg, groups)
        ko_market = MarketKnockoutProbabilityProvider.for_tournament(cfg, groups)
        return group_market, ko_market
    if mode.startswith("model_") or mode == "model_all":
        variant = resolve_model_variant(mode=mode)
        group_model = ModelGroupProbabilityProvider.from_csv(
            variant_pairwise_path(cfg.group_pairwise_predictions_file, variant.variant_id)
        )
        ko_model = ModelKnockoutProbabilityProvider.from_csv(
            variant_pairwise_path(cfg.knockout_pairwise_predictions_file, variant.variant_id)
        )
        return group_model, ko_model
    raise ValueError(f"Unknown mode: {mode}. Use market_all or a supported model_* mode.")
