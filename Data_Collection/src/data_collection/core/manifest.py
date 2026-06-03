from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.data_collection.core.paths import CollectionPaths, resolve_collection_paths

STAGE_COUNT_KEYS: dict[str, tuple[str, ...]] = {
    "collect_elo": ("fixtures", "team_ratings"),
    "collect_confederations": ("team_confederations",),
    "collect_odds_all": ("oddsportal_raw",),
    "match_odds": ("matched_odds", "unmatched_odds", "dropped_invalid_odds"),
    "collect_transfermarkt": (
        "squads_players",
        "valued_players",
        "unmatched_players",
        "players_updated",
    ),
    "resolve_transfermarkt_from_existing": (
        "squads_players",
        "valued_players",
        "unmatched_players",
        "players_updated",
    ),
}


def _sanitize_manifest_stage_payload(stage_payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(stage_payload)
    cleaned.pop("market_value_dir", None)
    return cleaned


def _sanitize_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(payload)
    cleaned.pop("market_value_dir", None)
    stages = cleaned.get("stages")
    if isinstance(stages, dict):
        cleaned["stages"] = {
            stage: _sanitize_manifest_stage_payload(stage_payload)
            if isinstance(stage_payload, dict)
            else stage_payload
            for stage, stage_payload in stages.items()
        }
    return cleaned


def _sanitize_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    if not extra:
        return {}
    cleaned = dict(extra)
    cleaned.pop("market_value_dir", None)
    return cleaned


def _read_json(path: Path) -> object:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def counts_from_outputs(paths: CollectionPaths) -> dict[str, Any]:
    """Derive manifest counts from on-disk collection outputs (no re-collection)."""
    counts: dict[str, Any] = {}

    fixtures = _read_json(paths.fixtures_path)
    if isinstance(fixtures, list):
        counts["fixtures"] = len(fixtures)

    ratings = _read_json(paths.team_ratings_path)
    if isinstance(ratings, list):
        counts["team_ratings"] = len(ratings)

    confederations = _read_json(paths.team_confederations_path)
    if isinstance(confederations, dict):
        teams = confederations.get("teams")
        if isinstance(teams, dict):
            counts["team_confederations"] = len(teams)

    raw_odds = _read_json(paths.odds_raw_path)
    if isinstance(raw_odds, list):
        counts["oddsportal_raw"] = len(raw_odds)

    matched_odds = _read_json(paths.odds_matched_path)
    unmatched_odds = _read_json(paths.odds_unmatched_path)
    if isinstance(matched_odds, list):
        counts["matched_odds"] = len(matched_odds)
    if isinstance(unmatched_odds, list):
        counts["unmatched_odds"] = len(unmatched_odds)
    if isinstance(raw_odds, list) and isinstance(matched_odds, list) and isinstance(unmatched_odds, list):
        counts["dropped_invalid_odds"] = len(raw_odds) - len(matched_odds) - len(unmatched_odds)

    squads = _read_json(paths.market_value_dir / "tournament_squads.json")
    with_value = _read_json(paths.market_value_dir / "tournament_squads_with_value.json")
    unmatched_players = _read_json(paths.market_value_dir / "tournament_squads_unmatched_players.json")

    if isinstance(squads, dict):
        counts["squads_players"] = int(squads.get("player_count", 0))

    if isinstance(with_value, dict):
        summary = with_value.get("market_value_summary") or {}
        counts["valued_players"] = int(summary.get("valued_players", 0))
        counts["unmatched_players"] = int(summary.get("unmatched_players", 0))
        counts["matched_players"] = int(summary.get("matched_players", 0))

    if isinstance(unmatched_players, dict):
        players = unmatched_players.get("players")
        if isinstance(players, list):
            counts["unmatched_players"] = len(players)

    if isinstance(with_value, dict):
        api_updated = 0
        for tournament in with_value.get("tournaments", []):
            for team in tournament.get("teams", []):
                for player in team.get("players", []):
                    if player.get("market_value_source") == "transfermarkt_ceapi":
                        api_updated += 1
        if api_updated:
            counts["players_updated"] = api_updated

    return counts


def _apply_derived_counts(manifest: dict[str, Any], derived: dict[str, Any], *, now: str) -> None:
    stages = dict(manifest.get("stages") or {})
    for stage, keys in STAGE_COUNT_KEYS.items():
        if stage not in stages:
            continue
        stage_counts = dict(stages[stage].get("counts") or {})
        for key in keys:
            if key in derived:
                stage_counts[key] = derived[key]
        stages[stage]["counts"] = stage_counts
        stages[stage]["synced_at"] = now
    manifest["stages"] = stages

    last_stage = manifest.get("last_stage")
    if last_stage in STAGE_COUNT_KEYS:
        top_counts = dict(manifest.get("counts") or {})
        for key in STAGE_COUNT_KEYS[last_stage]:
            if key in derived:
                top_counts[key] = derived[key]
        manifest["counts"] = top_counts


def sync_manifest_from_outputs(manifest_path: Path, paths: CollectionPaths) -> dict[str, Any]:
    """Refresh manifest top-level and stage counts from existing output files."""
    derived = counts_from_outputs(paths)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    manifest = _sanitize_manifest_payload(json.loads(manifest_path.read_text(encoding="utf-8")))
    now = datetime.now(timezone.utc).isoformat()
    manifest["updated_at"] = now
    _apply_derived_counts(manifest, derived, now=now)

    manifest_path.write_text(json.dumps(_sanitize_manifest_payload(manifest), indent=2), encoding="utf-8")
    return manifest


def sync_manifest(paths: CollectionPaths) -> dict[str, Any]:
    """Convenience wrapper used by pipelines and run-all."""
    return sync_manifest_from_outputs(paths.manifest_path, paths)


def write_manifest(
    manifest_path: Path,
    *,
    stage: str,
    partition: str,
    tournament_ids: list[str],
    counts: dict[str, int | float] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    safe_extra = _sanitize_extra(extra)

    payload: dict[str, Any] = {"updated_at": now, "partition": partition, "last_stage": stage}
    if counts:
        payload["counts"] = counts
    if safe_extra:
        payload.update(safe_extra)

    existing: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            existing = _sanitize_manifest_payload(json.loads(manifest_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            existing = {}

    stages = dict(existing.get("stages") or {})
    stages[stage] = {"at": now, "tournament_ids": tournament_ids, "counts": counts or {}, **safe_extra}
    payload["stages"] = stages

    manifest_path.write_text(json.dumps(_sanitize_manifest_payload(payload), indent=2), encoding="utf-8")

    root = manifest_path.parent.parent.parent
    paths = resolve_collection_paths(root, partition)
    sync_manifest_from_outputs(manifest_path, paths)
