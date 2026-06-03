from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TeamRating:
    tournament_id: str
    team_name: str
    country_code: str | None
    elo_rating: int
    elo_rank: int | None
    first_match_date: str | None
    source: str
    collected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FixtureStat:
    match_id: str
    tournament_id: str
    tournament_name: str
    competition: str
    season_year: int
    tournament_code: str
    date_utc: str | None
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    venue: str | None
    elo_rating: dict[str, int | None]
    elo_rating_diff: dict[str, int | None]
    elo_rank: dict[str, int | None]
    elo_rank_diff: dict[str, int | None]
    source: str
    collected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OddsRecord:
    match_id: str
    tournament_id: str
    tournament_name: str
    competition: str
    season_year: int
    bookmaker: str
    market: str
    home_odds: float | None
    draw_odds: float | None
    away_odds: float | None
    snapshot_time: str
    source: str
    home_team: str
    away_team: str
    date_utc: str | None
    collected_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
