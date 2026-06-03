from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_groups(path: Path) -> dict[str, list[str]]:
    data = load_json(path)
    return {str(k): list(v) for k, v in data["groups"].items()}


def load_knockout_bracket(path: Path) -> dict[str, Any]:
    return load_json(path)


def load_r32_scenarios(path: Path) -> dict[tuple[str, ...], dict[str, Any]]:
    data = load_json(path)
    index: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in data["scenarios"]:
        key = tuple(sorted(row["qualifying_third_groups"]))
        index[key] = row
    return index


def resolve_team_ref(
    ref: str,
    group_results: dict[str, Any],
    *,
    extra_refs: dict[str, str] | None = None,
) -> str:
    if extra_refs and ref in extra_refs:
        return extra_refs[ref]
    rank = int(ref[0])
    group = ref[1]
    return group_results[group].team_at_rank(rank)


def resolve_r32_pairing(
    match_def: dict[str, Any],
    group_results: dict[str, Any],
    scenario: dict[str, Any],
) -> tuple[str, str]:
    third_slots = scenario["third_slots"]
    home = resolve_team_ref(str(match_def["home"]), group_results)
    away_ref = match_def["away"]
    if isinstance(away_ref, dict) and away_ref.get("type") == "third_slot":
        slot = str(away_ref["slot"])
        group_letter = third_slots[slot]
        away = group_results[group_letter].team_at_rank(3)
    else:
        away = resolve_team_ref(str(away_ref), group_results)
    return home, away
