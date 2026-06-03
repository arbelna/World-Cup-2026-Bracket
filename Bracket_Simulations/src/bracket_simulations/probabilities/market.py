from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _normalize_probs(pa: float, pd: float, pb: float) -> tuple[float, float, float]:
    s = pa + pd + pb
    if s <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return pa / s, pd / s, pb / s


def _impute_from_win_rates(
    team_a: str,
    team_b: str,
    win_rate: dict[str, float],
    draw_rate: float,
) -> tuple[float, float, float]:
    pa = win_rate[team_a] * (1.0 - win_rate[team_b])
    pb = win_rate[team_b] * (1.0 - win_rate[team_a])
    return _normalize_probs(pa, draw_rate, pb)


class MarketProbabilityProvider:
    """Lookup de-vigged market probs (target_soft) for scheduled fixtures."""

    def __init__(
        self,
        matches: list[dict],
        *,
        impute_unplayed: bool = False,
        teams: list[str] | None = None,
    ) -> None:
        self._by_pair: dict[tuple[str, str], tuple[float, float, float]] = {}
        self._impute_unplayed = impute_unplayed
        self._win_rate: dict[str, float] = {}
        self._draw_rate = 1 / 3
        observed_wins: dict[str, list[float]] = {}
        observed_draws: list[float] = []

        for m in matches:
            target = m.get("target_soft")
            if target is None:
                continue
            a = str(m["team_a"])
            b = str(m["team_b"])
            ta, td, tb = (float(target[0]), float(target[1]), float(target[2]))
            self._by_pair[(a, b)] = (ta, td, tb)
            self._by_pair[(b, a)] = (tb, td, ta)
            observed_wins.setdefault(a, []).append(ta)
            observed_wins.setdefault(b, []).append(tb)
            observed_draws.append(td)

        if observed_draws:
            self._draw_rate = sum(observed_draws) / len(observed_draws)
        for team, wins in observed_wins.items():
            self._win_rate[team] = sum(wins) / len(wins)

        if impute_unplayed and teams:
            missing = 0
            for i, a in enumerate(teams):
                wa = self._win_rate.get(a, 1 / 3)
                for b in teams[i + 1 :]:
                    if (a, b) in self._by_pair:
                        continue
                    wb = self._win_rate.get(b, 1 / 3)
                    pa = wa * (1.0 - wb)
                    pb = wb * (1.0 - wa)
                    probs = _normalize_probs(pa, self._draw_rate, pb)
                    self._by_pair[(a, b)] = probs
                    self._by_pair[(b, a)] = (probs[2], probs[1], probs[0])
                    missing += 1
            if missing:
                logger.info(
                    "Imputed market-derived probs for %d unplayed pairings.",
                    missing,
                )

    @classmethod
    def from_dataset(
        cls,
        path: Path,
        *,
        competition: str | None = None,
        impute_unplayed: bool = False,
        teams: list[str] | None = None,
    ) -> MarketProbabilityProvider:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if competition:
            rows = [r for r in rows if r.get("competition") == competition]
        return cls(rows, impute_unplayed=impute_unplayed, teams=teams)

    @classmethod
    def for_tournament_market_all_group(cls, cfg, groups: dict[str, list[str]]) -> MarketProbabilityProvider:
        _ = groups
        return cls.from_dataset(
            cfg.train_dataset,
            competition=cfg.match_dataset_filter_competition,
            impute_unplayed=False,
        )

    def get(self, team_a: str, team_b: str) -> tuple[float, float, float]:
        key = (team_a, team_b)
        if key not in self._by_pair:
            if self._impute_unplayed:
                wa = self._win_rate.get(team_a, 1 / 3)
                wb = self._win_rate.get(team_b, 1 / 3)
                return _impute_from_win_rates(team_a, team_b, {team_a: wa, team_b: wb}, self._draw_rate)
            raise KeyError(f"No market probs for {team_a} vs {team_b}")
        return self._by_pair[key]

    def has(self, team_a: str, team_b: str) -> bool:
        return (team_a, team_b) in self._by_pair
