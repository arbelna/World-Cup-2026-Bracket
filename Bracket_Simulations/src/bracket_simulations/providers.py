from __future__ import annotations

from bracket_simulations.config import TournamentConfig
from bracket_simulations.probabilities.market import MarketProbabilityProvider
from bracket_simulations.probabilities.market_knockout import MarketKnockoutProbabilityProvider
from bracket_simulations.probabilities.model import ModelProbabilityProvider


def resolve_prob_providers(cfg: TournamentConfig, mode: str, groups: dict[str, list[str]]):
    if mode == "market_all":
        group_market = MarketProbabilityProvider.for_tournament_market_all_group(cfg, groups)
        ko_market = MarketKnockoutProbabilityProvider.for_tournament(cfg, groups)
        return group_market, ko_market
    if mode == "model_all":
        model = ModelProbabilityProvider.from_csv(cfg.pairwise_predictions_file)
        return model, model
    raise ValueError(f"Unknown mode: {mode}. Use market_all or model_all.")
