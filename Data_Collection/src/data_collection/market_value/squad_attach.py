from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from src.data_collection.market_value.player_matcher import (
    INVALID_PLAYER_NAMES,
    TransfermarktPlayerIndex,
    fetch_pre_tournament_valuations,
    normalize_player_name,
)

DEFAULT_DB_NAME = "transfermarkt-datasets.duckdb"
SQUADS_FILENAME = "tournament_squads.json"
SQUADS_WITH_VALUE_FILENAME = "tournament_squads_with_value.json"
UNMATCHED_FILENAME = "tournament_squads_unmatched_players.json"


def squad_paths(market_value_dir: Path) -> dict[str, Path]:
    return {
        "squads": market_value_dir / SQUADS_FILENAME,
        "with_value": market_value_dir / SQUADS_WITH_VALUE_FILENAME,
        "unmatched": market_value_dir / UNMATCHED_FILENAME,
        "duckdb": market_value_dir / DEFAULT_DB_NAME,
    }


def load_tournament_start_dates(fixtures_path: Path) -> dict[str, str]:
    if not fixtures_path.exists():
        raise FileNotFoundError(f"Fixtures file not found: {fixtures_path}")
    rows = json.loads(fixtures_path.read_text(encoding="utf-8"))
    earliest: dict[str, str] = {}
    for row in rows:
        tournament_id = str(row.get("tournament_id", "")).strip()
        date_utc = row.get("date_utc")
        if not tournament_id or not date_utc:
            continue
        day = str(date_utc)[:10]
        if tournament_id not in earliest or day < earliest[tournament_id]:
            earliest[tournament_id] = day
    if not earliest:
        raise ValueError(f"No tournament dates found in {fixtures_path}")
    return earliest


def attach_market_values(
    squads: dict[str, Any],
    *,
    conn: duckdb.DuckDBPyConnection,
    start_dates: dict[str, str],
    index: TransfermarktPlayerIndex | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    matcher = index or TransfermarktPlayerIndex(conn)
    output = deepcopy(squads)
    unmatched_players: list[dict[str, Any]] = []
    matched_count = 0
    valued_count = 0
    tournaments = output["tournaments"]
    total_tournaments = len(tournaments)
    print(f"[TM] Attach stage start tournaments={total_tournaments}")
    for t_index, tournament in enumerate(tournaments, start=1):
        tournament_id = tournament["tournament_id"]
        cutoff_date = start_dates.get(tournament_id)
        if cutoff_date is None:
            raise KeyError(f"No start date for tournament {tournament_id!r}")
        team_count = len(tournament.get("teams", []))
        print(
            f"[TM] Attach progress {t_index}/{total_tournaments} tournament={tournament_id} "
            f"teams={team_count} cutoff={cutoff_date}"
        )
        id_by_player_key: dict[tuple[str, str, int, int], int] = {}
        match_meta: dict[tuple[str, str, int, int], dict[str, Any]] = {}
        tournament_matched_before = matched_count
        tournament_valued_before = valued_count
        unmatched_before = len(unmatched_players)
        for team_index, team in enumerate(tournament["teams"]):
            for player_index, player in enumerate(team["players"]):
                key = (tournament_id, team["team_name"], team_index, player_index)
                match = matcher.match(
                    str(player.get("player_name", "")),
                    date_of_birth=player.get("date_of_birth"),
                    wikipedia_title=player.get("wikipedia_title"),
                )
                if match is None:
                    reason = (
                        "invalid_squad_record"
                        if normalize_player_name(str(player.get("player_name", ""))) in INVALID_PLAYER_NAMES
                        else "player_not_found"
                    )
                    unmatched_players.append(
                        {
                            "tournament_id": tournament_id,
                            "tournament_name": tournament.get("tournament_name"),
                            "season_year": tournament.get("season_year"),
                            "tournament_start_date": cutoff_date,
                            "team_name": team["team_name"],
                            "group": team.get("group"),
                            "player_name": player.get("player_name"),
                            "date_of_birth": player.get("date_of_birth"),
                            "wikipedia_title": player.get("wikipedia_title"),
                            "club_name": player.get("club_name"),
                            "reason": reason,
                        }
                    )
                    continue
                id_by_player_key[key] = match.player_id
                match_meta[key] = {
                    "transfermarkt_player_id": match.player_id,
                    "transfermarkt_name": match.matched_name,
                    "match_method": match.method,
                    "match_score": match.score,
                }
                matched_count += 1
        valuations = fetch_pre_tournament_valuations(conn, sorted(set(id_by_player_key.values())), cutoff_date)
        for team_index, team in enumerate(tournament["teams"]):
            for player_index, player in enumerate(team["players"]):
                key = (tournament_id, team["team_name"], team_index, player_index)
                player["market_value"] = None
                if key not in id_by_player_key:
                    continue
                player_id = id_by_player_key[key]
                valuation = valuations.get(player_id)
                if valuation is None or valuation.get("market_value") is None:
                    unmatched_players.append(
                        {
                            "tournament_id": tournament_id,
                            "tournament_name": tournament.get("tournament_name"),
                            "season_year": tournament.get("season_year"),
                            "tournament_start_date": cutoff_date,
                            "team_name": team["team_name"],
                            "group": team.get("group"),
                            "player_name": player.get("player_name"),
                            "date_of_birth": player.get("date_of_birth"),
                            "wikipedia_title": player.get("wikipedia_title"),
                            "club_name": player.get("club_name"),
                            "transfermarkt_player_id": player_id,
                            "transfermarkt_name": match_meta[key].get("transfermarkt_name"),
                            "match_method": match_meta[key].get("match_method"),
                            "reason": "no_valuation_before_tournament",
                        }
                    )
                    continue
                player["market_value"] = valuation["market_value"]
                valued_count += 1
        tournament_matched = matched_count - tournament_matched_before
        tournament_valued = valued_count - tournament_valued_before
        tournament_unmatched = len(unmatched_players) - unmatched_before
        print(
            f"[TM] Attach tournament done {tournament_id}: matched={tournament_matched} "
            f"valued={tournament_valued} unmatched_added={tournament_unmatched}"
        )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_players": squads.get("player_count"),
        "matched_players": matched_count,
        "valued_players": valued_count,
        "unmatched_players": len(unmatched_players),
    }
    unmatched_payload = {"summary": summary, "players": unmatched_players}
    output["market_values_attached_at"] = summary["generated_at"]
    output["market_value_summary"] = {
        "matched_players": matched_count,
        "valued_players": valued_count,
        "unmatched_players": len(unmatched_players),
    }
    print(
        f"[TM] Attach stage complete matched={matched_count} valued={valued_count} "
        f"unmatched={len(unmatched_players)}"
    )
    return output, unmatched_payload
