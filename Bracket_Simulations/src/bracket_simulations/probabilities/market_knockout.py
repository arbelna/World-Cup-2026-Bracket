from __future__ import annotations

import json
import logging

from bracket_simulations.probabilities.davidson import DavidsonModel
from bracket_simulations.probabilities.market import MarketProbabilityProvider

logger = logging.getLogger(__name__)


class MarketKnockoutProbabilityProvider:
    """Market 1X2 when available; Davidson 90-min + ET otherwise."""

    def __init__(self, market: MarketProbabilityProvider, davidson: DavidsonModel) -> None:
        self._market = market
        self._davidson = davidson

    @classmethod
    def for_tournament(cls, cfg, groups: dict[str, list[str]]) -> MarketKnockoutProbabilityProvider:
        teams = sorted({t for ts in groups.values() for t in ts})
        rows = json.loads(cfg.train_dataset.read_text(encoding="utf-8"))
        competition = cfg.match_dataset_filter_competition
        if competition:
            rows = [r for r in rows if r.get("competition") == competition]
        market = MarketProbabilityProvider.from_dataset(
            cfg.train_dataset,
            competition=competition,
            impute_unplayed=False,
        )
        davidson = DavidsonModel.fit_from_matches(rows, teams)
        ko = cls(market, davidson)
        n_direct = sum(
            1 for i, a in enumerate(teams) for b in teams[i + 1 :] if market.has(a, b)
        )
        n_pairs = len(teams) * (len(teams) - 1) // 2
        logger.info(
            "Knockout provider: %d/%d pairings have market odds; %d use Davidson.",
            n_direct,
            n_pairs,
            n_pairs - n_direct,
        )
        return ko

    def get(
        self,
        team_a: str,
        team_b: str,
        *,
        stage: str | None = None,
        slot_id: str | None = None,
    ) -> tuple[float, float, float]:
        _ = stage, slot_id
        if self._market.has(team_a, team_b):
            return self._market.get(team_a, team_b)
        return self._davidson.probs_90min(team_a, team_b)

    def has(self, team_a: str, team_b: str) -> bool:
        return True

    def et_win_prob_team_a(
        self,
        team_a: str,
        team_b: str,
        *,
        stage: str | None = None,
        slot_id: str | None = None,
    ) -> float:
        _ = stage, slot_id
        return self._davidson.et_win_prob_team_a(team_a, team_b)
