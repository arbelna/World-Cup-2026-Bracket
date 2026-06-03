from __future__ import annotations

import json
from pathlib import Path

from src.data_collection.config.tournaments import tournaments_for_partition
from src.data_collection.core.manifest import write_manifest
from src.data_collection.core.paths import resolve_collection_paths
from src.data_collection.collectors.confederation_collector import ConfederationCollector
from src.data_collection.collectors.elo_collector import EloCollector
from src.data_collection.utils.validation import validate_fixtures, validate_team_ratings


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_elo(root: Path, partition: str, *, sanity_check: bool = False) -> None:
    paths = resolve_collection_paths(root, partition)
    tournaments = tournaments_for_partition(partition)
    print(f"[ELO] Starting collection for partition={partition} tournaments={len(tournaments)}")
    collector = EloCollector(tournaments=tournaments, team_request_delay_seconds=0.5)
    team_ratings, fixtures = collector.collect(sanity_check=sanity_check)

    ratings_payload = [r.to_dict() for r in team_ratings]
    fixtures_payload = [f.to_dict() for f in fixtures]
    validate_team_ratings(ratings_payload)
    validate_fixtures(fixtures_payload)
    _write_json(paths.team_ratings_path, ratings_payload)
    _write_json(paths.fixtures_path, fixtures_payload)
    print(
        f"[ELO] Completed partition={partition} fixtures={len(fixtures_payload)} "
        f"team_ratings={len(ratings_payload)}"
    )

    write_manifest(
        paths.manifest_path,
        stage="collect_elo",
        partition=partition,
        tournament_ids=[t.tournament_id for t in tournaments],
        counts={"fixtures": len(fixtures_payload), "team_ratings": len(ratings_payload)},
    )


def collect_confederations(root: Path, partition: str) -> None:
    paths = resolve_collection_paths(root, partition)
    print(f"[CONFED] Starting collection for partition={partition}")
    collector = ConfederationCollector(request_delay_seconds=0.3)
    conf_map = collector.collect()
    payload = conf_map.to_dict()
    _write_json(paths.team_confederations_path, payload)
    print(
        f"[CONFED] Completed partition={partition} team_confederations={len(payload.get('teams', {}))}"
    )
    tournaments = tournaments_for_partition(partition)
    write_manifest(
        paths.manifest_path,
        stage="collect_confederations",
        partition=partition,
        tournament_ids=[t.tournament_id for t in tournaments],
        counts={"team_confederations": len(payload.get("teams", {}))},
    )
