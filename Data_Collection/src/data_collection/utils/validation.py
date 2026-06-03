from __future__ import annotations

from typing import Any

from src.data_collection.utils.matching import ensure_unique_match_ids

BLOCKED_ODDS_BOOKMAKERS = frozenset({"betfair exchange"})
MIN_1X2_ODDS = 1.01
MAX_1X2_ODDS = 500.0


def validate_team_ratings(records: list[dict[str, Any]]) -> None:
    required = {"tournament_id", "team_name", "elo_rating", "country_code", "source", "collected_at"}
    for record in records:
        missing = required.difference(record.keys())
        if missing:
            raise ValueError(f"Team rating missing required fields: {missing}")
        if not isinstance(record["elo_rating"], int):
            raise ValueError(f"Invalid elo_rating for {record['team_name']}")


def validate_fixtures(records: list[dict[str, Any]]) -> None:
    required = {
        "match_id",
        "tournament_id",
        "tournament_name",
        "competition",
        "season_year",
        "tournament_code",
        "home_team",
        "away_team",
        "elo_rating",
        "elo_rating_diff",
        "elo_rank",
        "elo_rank_diff",
        "source",
        "collected_at",
    }
    for record in records:
        missing = required.difference(record.keys())
        if missing:
            raise ValueError(f"Fixture missing required fields: {missing}")
    ensure_unique_match_ids(records)


def is_blocked_odds_bookmaker(bookmaker: str) -> bool:
    return bookmaker.strip().lower() in BLOCKED_ODDS_BOOKMAKERS


def is_plausible_1x2_odds(home_odds: float, draw_odds: float, away_odds: float) -> bool:
    prices = (float(home_odds), float(draw_odds), float(away_odds))
    if any(price < MIN_1X2_ODDS or price > MAX_1X2_ODDS for price in prices):
        return False
    if sum(1 for price in prices if price < 2.0) >= 2:
        return False
    implied = sum(1.0 / price for price in prices)
    return 0.95 <= implied <= 1.25


def validate_odds(records: list[dict[str, Any]]) -> None:
    required = {
        "match_id",
        "tournament_id",
        "bookmaker",
        "market",
        "home_odds",
        "draw_odds",
        "away_odds",
        "source",
        "home_team",
        "away_team",
    }
    for record in records:
        missing = required.difference(record.keys())
        if missing:
            raise ValueError(f"Odds record missing required fields: {missing}")
