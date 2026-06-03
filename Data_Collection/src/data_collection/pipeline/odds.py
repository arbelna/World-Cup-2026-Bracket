from __future__ import annotations

import json
from pathlib import Path

from src.data_collection.config.tournaments import tournaments_for_partition
from src.data_collection.core.manifest import write_manifest
from src.data_collection.core.paths import resolve_collection_paths
from src.data_collection.collectors.oddsportal_collector import OddsPortalCollector
from src.data_collection.utils.matching import find_fixture_match_id
from src.data_collection.utils.validation import (
    is_blocked_odds_bookmaker,
    is_plausible_1x2_odds,
    validate_odds,
)


def _read_json(path: Path) -> object:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_odds_all(
    root: Path,
    partition: str,
    *,
    sanity_check: bool = False,
    odds_workers: int = 2,
    max_match_pages: int | None = None,
) -> None:
    paths = resolve_collection_paths(root, partition)
    tournaments = tournaments_for_partition(partition)
    print(
        f"[ODDS] Starting collect-all partition={partition} tournaments={len(tournaments)} "
        f"workers={odds_workers} sanity={sanity_check}"
    )
    collector = OddsPortalCollector(
        tournaments=tournaments,
        max_match_pages=max_match_pages,
        odds_workers=odds_workers,
        output_file=paths.odds_raw_path,
    )
    records = collector.collect_tournament_odds(sanity_check=sanity_check)
    payload = [r.to_dict() for r in records]
    _write_json(paths.odds_raw_path, payload)
    print(f"[ODDS] collect-all completed partition={partition} raw_rows={len(payload)}")
    write_manifest(
        paths.manifest_path,
        stage="collect_odds_all",
        partition=partition,
        tournament_ids=[t.tournament_id for t in tournaments],
        counts={"oddsportal_raw": len(payload)},
    )


def match_odds(root: Path, partition: str) -> None:
    paths = resolve_collection_paths(root, partition)
    fixtures = _read_json(paths.fixtures_path)
    raw_odds = _read_json(paths.odds_raw_path)
    if not isinstance(fixtures, list):
        raise ValueError("fixtures_stats.json must be a list")
    if not isinstance(raw_odds, list):
        raise ValueError("oddsportal_raw_odds.json must be a list")

    print(
        f"[ODDS] Starting match step partition={partition} fixtures={len(fixtures)} raw_odds={len(raw_odds)}"
    )
    matched: list[dict] = []
    unmatched: list[dict] = []
    dropped = 0
    for row in raw_odds:
        bookmaker = str(row.get("bookmaker", ""))
        if is_blocked_odds_bookmaker(bookmaker) or not is_plausible_1x2_odds(
            row["home_odds"], row["draw_odds"], row["away_odds"]
        ):
            dropped += 1
            continue
        match_id = find_fixture_match_id(
            fixtures,
            str(row["home_team"]),
            str(row["away_team"]),
            row.get("date_utc"),
            str(row.get("tournament_id", "")),
        )
        if not match_id:
            unmatched.append(row)
            continue
        normalized = dict(row)
        normalized["match_id"] = match_id
        matched.append(normalized)

    validate_odds(matched)
    _write_json(paths.odds_matched_path, matched)
    _write_json(paths.odds_unmatched_path, unmatched)
    print(
        f"[ODDS] match completed partition={partition} matched={len(matched)} "
        f"unmatched={len(unmatched)} dropped_invalid={dropped}"
    )
    tournaments = tournaments_for_partition(partition)
    write_manifest(
        paths.manifest_path,
        stage="match_odds",
        partition=partition,
        tournament_ids=[t.tournament_id for t in tournaments],
        counts={"matched_odds": len(matched), "unmatched_odds": len(unmatched), "dropped_invalid_odds": dropped},
    )


def generate_missing_template(root: Path, partition: str) -> None:
    paths = resolve_collection_paths(root, partition)
    fixtures = _read_json(paths.fixtures_path)
    matched = _read_json(paths.odds_matched_path)
    if not isinstance(fixtures, list):
        raise ValueError("fixtures_stats.json must be a list")
    if not isinstance(matched, list):
        raise ValueError("matched_odds.json must be a list")
    matched_ids = {str(row.get("match_id", "")) for row in matched if row.get("match_id")}
    template = {
        "instructions": "Fill source_url for each missing fixture, then run collect-odds-missing.",
        "entries": [
            {
                "match_id": row.get("match_id"),
                "tournament_id": row.get("tournament_id"),
                "source_url": "",
            }
            for row in fixtures
            if str(row.get("match_id", "")) and str(row.get("match_id", "")) not in matched_ids
        ],
    }
    _write_json(paths.missing_manual_path, template)
    print(
        f"[ODDS] missing template generated partition={partition} entries={len(template['entries'])}"
    )


def collect_odds_missing(root: Path, partition: str, *, odds_workers: int = 2) -> None:
    paths = resolve_collection_paths(root, partition)
    manual = _read_json(paths.missing_manual_path)
    if not isinstance(manual, dict):
        raise ValueError("missing_odds_manual.json must be an object")
    entries = manual.get("entries") or []
    urls = [str(e.get("source_url", "")).strip() for e in entries if str(e.get("source_url", "")).strip()]
    if not urls:
        raise ValueError("No source_url entries found in missing_odds_manual.json")
    print(
        f"[ODDS] Starting collect-missing partition={partition} urls={len(urls)} workers={odds_workers}"
    )

    tournaments = {t.tournament_id: t for t in tournaments_for_partition(partition)}
    grouped: dict[str, list[str]] = {}
    for entry in entries:
        tid = str(entry.get("tournament_id", "")).strip()
        url = str(entry.get("source_url", "")).strip()
        if tid and url and tid in tournaments:
            grouped.setdefault(tid, []).append(url)

    new_payload: list[dict] = []
    for tournament_id, tournament_urls in grouped.items():
        print(
            f"[ODDS] collect-missing tournament={tournament_id} urls={len(tournament_urls)}"
        )
        collector = OddsPortalCollector(tournaments=(tournaments[tournament_id],), odds_workers=odds_workers)
        rows = collector.collect_match_urls(tournament_urls, tournament=tournaments[tournament_id])
        new_payload.extend([r.to_dict() for r in rows])
        print(
            f"[ODDS] collect-missing tournament={tournament_id} fetched_rows={len(rows)}"
        )

    existing = _read_json(paths.odds_raw_path)
    if not isinstance(existing, list):
        existing = []
    _write_json(paths.odds_raw_path, existing + new_payload)
    print(
        f"[ODDS] collect-missing appended_rows={len(new_payload)} raw_total={len(existing) + len(new_payload)}"
    )
    match_odds(root, partition)
    generate_missing_template(root, partition)
