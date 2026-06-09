from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bracket_simulations.utils.matching import normalize_team_name


def load_tournament_fixtures(path: Path, tournament_id: str) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"fixtures file must be a list: {path}")
    return [row for row in rows if str(row.get("tournament_id", "")) == tournament_id]


def load_tournament_team_ratings(path: Path, tournament_id: str) -> dict[str, int]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"team ratings file must be a list: {path}")

    ratings: dict[str, int] = {}
    for row in rows:
        if str(row.get("tournament_id", "")) != tournament_id:
            continue
        team_name = str(row.get("team_name", "")).strip()
        elo_rating = row.get("elo_rating")
        if not team_name or elo_rating is None:
            continue
        ratings[team_name] = int(elo_rating)
    return ratings


def load_knockout_context(path: Path) -> dict[str, dict[str, str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"knockout context must be an object: {path}")
    return {
        str(stage): {str(slot_id): str(country) for slot_id, country in slots.items()}
        for stage, slots in raw.items()
    }


def build_group_schedule(
    groups: dict[str, list[str]],
    fixtures: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str]]]:
    team_to_group = {
        normalize_team_name(team): group_label
        for group_label, teams in groups.items()
        for team in teams
    }
    schedule: dict[str, list[tuple[str, str]]] = {label: [] for label in groups}
    seen_pairs: set[tuple[str, str]] = set()

    def _sort_key(row: dict[str, Any]) -> str:
        return str(row.get("date_utc", ""))

    for row in sorted(fixtures, key=_sort_key):
        team_a = str(row.get("home_team", ""))
        team_b = str(row.get("away_team", ""))
        group_a = team_to_group.get(normalize_team_name(team_a))
        group_b = team_to_group.get(normalize_team_name(team_b))
        if not group_a or group_a != group_b:
            continue
        pair_key = tuple(sorted((normalize_team_name(team_a), normalize_team_name(team_b))))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        schedule[group_a].append((team_a, team_b))

    return schedule


def host_diff_for_country(team_a: str, team_b: str, host_country: str | None) -> float:
    if not host_country:
        return 0.0
    host_key = normalize_team_name(host_country)
    team_a_host = normalize_team_name(team_a) == host_key
    team_b_host = normalize_team_name(team_b) == host_key
    return float(team_a_host) - float(team_b_host)
