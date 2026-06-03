from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import urlretrieve

import duckdb
import requests

from src.data_collection.config.tournaments import tournaments_for_partition
from src.data_collection.core.manifest import write_manifest
from src.data_collection.core.paths import resolve_collection_paths
from src.data_collection.collectors.wikipedia_squad_collector import WikipediaSquadCollector
from src.data_collection.market_value.squad_attach import (
    attach_market_values,
    load_tournament_start_dates,
    squad_paths,
)
from src.data_collection.schemas.squads import new_squad_collection_result


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _recompute_with_value_summary(with_value: dict) -> None:
    total = int(with_value.get("player_count", 0))
    valued = 0
    for tournament in with_value.get("tournaments", []):
        for team in tournament.get("teams", []):
            for player in team.get("players", []):
                if player.get("market_value") is not None:
                    valued += 1
    summary = with_value.setdefault("market_value_summary", {})
    summary["valued_players"] = valued
    summary["unmatched_players"] = max(total - valued, 0)
    summary["value_rate"] = round((valued / total), 4) if total else 0.0


def _maybe_update_tm_db(db_path: Path, db_url: str | None, *, force: bool = False) -> None:
    if not db_url:
        return
    if db_path.exists() and not force:
        print(f"[TM] Reusing existing DB at {db_path} (skip download)")
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[TM] Downloading DB to {db_path}")
    print(f"[TM] Running: curl -L -o \"{db_path}\" \"{db_url}\"")
    try:
        subprocess.run(
            ["curl", "-L", "-o", str(db_path), db_url],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        print("[TM] curl failed or unavailable, using urllib fallback")
        urlretrieve(db_url, str(db_path))
    print("[TM] DB download complete")


API_TEMPLATE = "https://www.transfermarkt.co.uk/ceapi/marketValueDevelopment/graph/{player_id}"
TM_MANUAL_LINKS_FILENAME = "transfermarkt_manual_links.json"
TM_SEARCH_URL = "https://www.transfermarkt.co.uk/schnellsuche/ergebnis/schnellsuche?query={query}"
TM_PROFILE_URL = "https://www.transfermarkt.co.uk/-/profil/spieler/{player_id}"


def _extract_player_id(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    match = re.search(r"/spieler/(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"/graph/(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _normalize_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def _is_likely_player_name(value: str) -> bool:
    cleaned = str(value or "").strip()
    if not cleaned:
        return False
    if "%" in cleaned:
        return False
    if cleaned.lower().startswith("player representation by"):
        return False
    normalized = _normalize_name(cleaned)
    if len(normalized) < 4:
        return False
    return True


def _build_query_variants(player_name: str, wikipedia_title: str | None) -> list[str]:
    variants: list[str] = []
    base = player_name.strip()
    if base:
        variants.append(base)
        tokens = [tok for tok in re.split(r"\s+", base) if tok]
        if len(tokens) >= 2:
            variants.append(f"{tokens[-1]} {' '.join(tokens[:-1])}")
            variants.append(f"{tokens[-1]},{tokens[0]}")
    if wikipedia_title:
        title = wikipedia_title.split("/")[-1].replace("_", " ")
        title = re.sub(r"\s*\(.*\)\s*$", "", title).strip()
        if title:
            variants.append(title)
    out: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        key = variant.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(variant)
    return out


def _build_query_variants_with_club(
    player_name: str,
    wikipedia_title: str | None,
    club_name: str | None,
) -> list[str]:
    variants = _build_query_variants(player_name, wikipedia_title)
    club = str(club_name or "").strip()
    base = str(player_name or "").strip()
    if base and club:
        variants.append(f"{base} {club}")
    out: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        key = variant.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(variant)
    return out


def _extract_player_ids_from_search_html(html: str) -> list[int]:
    ids = re.findall(r"/[^\"']*/profil/spieler/(\d+)", html)
    out: list[int] = []
    seen: set[int] = set()
    for raw in ids:
        pid = int(raw)
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
    return out


def _parse_tm_date(value: str) -> datetime.date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def _parse_profile_dob(html: str) -> str | None:
    match = re.search(r"Date of birth/Age:\s*([0-3]?\d/[01]?\d/\d{4})", html, re.IGNORECASE)
    if match:
        return _parse_tm_date(match.group(1)).isoformat()
    match_iso = re.search(r"(\d{4}-\d{2}-\d{2})", html)
    if match_iso:
        return match_iso.group(1)
    return None


def _load_manual_player_ids(manual_path: Path) -> dict[tuple[str, str, str], int]:
    if not manual_path.exists():
        return {}
    payload = json.loads(manual_path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("players", [])
    manual_ids: dict[tuple[str, str, str], int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        player_id = _extract_player_id(row.get("transfermarkt_player_id") or row.get("source_url"))
        if player_id is None:
            continue
        key = (
            str(row.get("tournament_id", "")).strip(),
            str(row.get("team_name", "")).strip(),
            str(row.get("player_name", "")).strip(),
        )
        if all(key):
            manual_ids[key] = player_id
    return manual_ids


def backfill_missing_from_api(
    with_value_path: Path,
    unmatched_path: Path,
    *,
    request_delay: float = 0.2,
    checkpoint_every: int = 20,
) -> dict[str, int]:
    with_value = json.loads(with_value_path.read_text(encoding="utf-8"))
    unmatched = json.loads(unmatched_path.read_text(encoding="utf-8"))
    players = list(unmatched.get("players", []))
    manual_path = unmatched_path.parent / TM_MANUAL_LINKS_FILENAME
    manual_ids = _load_manual_player_ids(manual_path)
    if manual_ids:
        print(f"[TM] Loaded manual Transfermarkt links entries={len(manual_ids)} from {manual_path}")

    targets: list[dict] = []
    manual_targets = 0
    for row in players:
        reason = str(row.get("reason", "")).strip()
        if reason not in {"no_valuation_before_tournament", "player_not_found"}:
            continue
        key = (
            str(row.get("tournament_id", "")).strip(),
            str(row.get("team_name", "")).strip(),
            str(row.get("player_name", "")).strip(),
        )
        player_id = _extract_player_id(row.get("transfermarkt_player_id"))
        if player_id is None:
            player_id = _extract_player_id(row.get("transfermarkt_source_url"))
        if player_id is None:
            player_id = manual_ids.get(key)
            if player_id is not None:
                manual_targets += 1
        if player_id is None and reason != "player_not_found":
            continue
        if player_id is not None:
            row["transfermarkt_player_id"] = player_id
        targets.append(row)

    if not targets:
        print("[TM] API backfill skipped: no eligible unmatched players")
        return {"api_calls": 0, "players_updated": 0, "unmatched_removed": 0}
    print(f"[TM] API backfill start targets={len(targets)} manual_targets={manual_targets}")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    history_cache: dict[int, list[tuple[str, int]]] = {}
    search_cache: dict[str, list[int]] = {}
    profile_dob_cache: dict[int, str | None] = {}
    recovered_keys: set[tuple[str, str, str]] = set()
    updated = 0
    calls = 0
    search_resolved = 0
    search_failures = 0

    def _http_get_text(url: str) -> str:
        nonlocal search_failures
        for _ in range(2):
            try:
                return session.get(url, timeout=(8, 20)).text
            except requests.RequestException:
                search_failures += 1
                if request_delay > 0:
                    time.sleep(request_delay)
        return ""

    def resolve_player_id_from_live_search(row: dict) -> int | None:
        if not _is_likely_player_name(str(row.get("player_name", ""))):
            return None
        queries = _build_query_variants_with_club(
            str(row.get("player_name", "")),
            row.get("wikipedia_title"),
            row.get("club_name"),
        )
        if not queries:
            return None
        candidate_ids: list[int] = []
        for query in queries:
            key = query.lower()
            if key not in search_cache:
                url = TM_SEARCH_URL.format(query=quote_plus(query))
                html = _http_get_text(url)
                search_cache[key] = _extract_player_ids_from_search_html(html) if html else []
                if request_delay > 0:
                    time.sleep(request_delay)
            for pid in search_cache[key]:
                if pid not in candidate_ids:
                    candidate_ids.append(pid)
            if len(candidate_ids) >= 12:
                break
        if not candidate_ids:
            return None
        target_dob = str(row.get("date_of_birth") or "").strip()
        if not target_dob:
            return candidate_ids[0]
        for pid in candidate_ids[:12]:
            if pid not in profile_dob_cache:
                html = _http_get_text(TM_PROFILE_URL.format(player_id=pid))
                profile_dob_cache[pid] = _parse_profile_dob(html) if html else None
                if request_delay > 0:
                    time.sleep(request_delay)
            if profile_dob_cache.get(pid) == target_dob:
                return pid
        return None

    def _write_checkpoint(processed: int) -> None:
        filtered_checkpoint: list[dict] = []
        for original in players:
            key = (
                str(original.get("tournament_id")),
                str(original.get("team_name")),
                str(original.get("player_name")),
            )
            if key in recovered_keys:
                continue
            filtered_checkpoint.append(original)
        unmatched["players"] = filtered_checkpoint
        unmatched.setdefault("summary", {})["unmatched_players"] = len(filtered_checkpoint)
        _recompute_with_value_summary(with_value)
        _write_json(with_value_path, with_value)
        _write_json(unmatched_path, unmatched)
        print(
            f"[TM] API backfill checkpoint processed={processed}/{len(targets)} "
            f"updated={updated} api_calls={calls} search_resolved={search_resolved} "
            f"remaining_unmatched={len(filtered_checkpoint)}"
        )

    processed_targets = 0
    for row in targets:
        processed_targets += 1
        player_id_raw = _extract_player_id(row.get("transfermarkt_player_id"))
        if player_id_raw is None and str(row.get("reason", "")).strip() == "player_not_found":
            resolved_id = resolve_player_id_from_live_search(row)
            if resolved_id is not None:
                row["transfermarkt_player_id"] = resolved_id
                player_id_raw = resolved_id
                search_resolved += 1

        if player_id_raw is not None:
            player_id = int(player_id_raw)
            cutoff = str(row.get("tournament_start_date", ""))
            if player_id not in history_cache:
                response = session.get(API_TEMPLATE.format(player_id=player_id), timeout=(8, 20))
                calls += 1
                if response.status_code != 200:
                    history_cache[player_id] = []
                else:
                    parsed: list[tuple[str, int]] = []
                    for item in (response.json().get("list", []) or []):
                        d = item.get("datum_mw")
                        v = item.get("y")
                        if d is None or v is None:
                            continue
                        try:
                            day = datetime.strptime(str(d), "%d/%m/%Y").date().isoformat()
                            parsed.append((day, int(v)))
                        except Exception:
                            continue
                    parsed.sort(key=lambda x: x[0])
                    history_cache[player_id] = parsed
                if request_delay > 0:
                    time.sleep(request_delay)
            pre = [entry for entry in history_cache[player_id] if entry[0] <= cutoff]
            if pre:
                best_date, best_value = pre[-1]
                key = (str(row.get("tournament_id")), str(row.get("team_name")), str(row.get("player_name")))
                recovered_keys.add(key)
                for tournament in with_value.get("tournaments", []):
                    if tournament.get("tournament_id") != row.get("tournament_id"):
                        continue
                    for team in tournament.get("teams", []):
                        if team.get("team_name") != row.get("team_name"):
                            continue
                        for player in team.get("players", []):
                            if player.get("player_name") == row.get("player_name"):
                                player["market_value"] = best_value
                                player["market_value_source"] = "transfermarkt_ceapi"
                                player["market_value_date"] = best_date
                                player["market_value_source_url"] = API_TEMPLATE.format(player_id=player_id)
                                player["transfermarkt_player_id"] = player_id
                                updated += 1

        if processed_targets % 10 == 0:
            print(
                f"[TM] API backfill progress processed={processed_targets}/{len(targets)} "
                f"updated={updated} api_calls={calls} search_resolved={search_resolved}"
            )
        if checkpoint_every > 0 and processed_targets % checkpoint_every == 0:
            _write_checkpoint(processed_targets)
    filtered: list[dict] = []
    for row in players:
        key = (str(row.get("tournament_id")), str(row.get("team_name")), str(row.get("player_name")))
        if key in recovered_keys:
            continue
        filtered.append(row)
    unmatched["players"] = filtered
    unmatched.setdefault("summary", {})["unmatched_players"] = len(filtered)
    _recompute_with_value_summary(with_value)
    _write_json(with_value_path, with_value)
    _write_json(unmatched_path, unmatched)
    print(
        f"[TM] API backfill complete api_calls={calls} players_updated={updated} "
        f"search_resolved={search_resolved} "
        f"search_failures={search_failures} "
        f"unmatched_removed={len(players) - len(filtered)}"
    )
    return {
        "api_calls": calls,
        "players_updated": updated,
        "search_resolved": search_resolved,
        "unmatched_removed": len(players) - len(filtered),
    }


def collect_transfermarkt(
    root: Path,
    partition: str,
    *,
    skip_api_backfill: bool = False,
    tm_db_url: str | None = None,
) -> None:
    paths = resolve_collection_paths(root, partition)
    tournaments = tournaments_for_partition(partition)
    tournament_ids = [t.tournament_id for t in tournaments]
    print(f"[TM] Starting collection partition={partition} tournaments={len(tournament_ids)}")

    collector = WikipediaSquadCollector(tournaments=tournaments)
    squads = collector.collect(tournament_ids)
    squads_payload = new_squad_collection_result(squads).to_dict()
    print(
        f"[TM] Wikipedia squads collected tournaments={squads_payload.get('tournament_count')} "
        f"players={squads_payload.get('player_count')}"
    )

    mv_paths = squad_paths(paths.market_value_dir)
    mv_paths["duckdb"] = paths.tm_db_path
    _maybe_update_tm_db(paths.tm_db_path, tm_db_url, force=False)
    _write_json(mv_paths["squads"], squads_payload)
    if not mv_paths["duckdb"].exists():
        raise FileNotFoundError(
            f"Missing DuckDB database: {mv_paths['duckdb']}. "
            "Provide local file or use --tm-db-url."
        )
    start_dates = load_tournament_start_dates(paths.fixtures_path)
    print(f"[TM] Loaded tournament start dates count={len(start_dates)}")
    conn = duckdb.connect(str(mv_paths["duckdb"]), read_only=True)
    try:
        enriched, unmatched = attach_market_values(
            squads_payload,
            conn=conn,
            start_dates=start_dates,
        )
    finally:
        conn.close()

    _write_json(mv_paths["with_value"], enriched)
    _write_json(mv_paths["unmatched"], unmatched)
    print(
        f"[TM] DB attach complete valued={enriched.get('market_value_summary', {}).get('valued_players', 0)} "
        f"unmatched={unmatched.get('summary', {}).get('unmatched_players', 0)}"
    )

    counts: dict[str, int] = {
        "squads_players": int(squads_payload.get("player_count", 0)),
        "valued_players": int(enriched.get("market_value_summary", {}).get("valued_players", 0)),
        "unmatched_players": int(unmatched.get("summary", {}).get("unmatched_players", 0)),
    }
    if not skip_api_backfill:
        backfill_counts = backfill_missing_from_api(mv_paths["with_value"], mv_paths["unmatched"])
        counts.update(backfill_counts)
    else:
        print("[TM] API backfill skipped by flag")

    write_manifest(
        paths.manifest_path,
        stage="collect_transfermarkt",
        partition=partition,
        tournament_ids=tournament_ids,
        counts=counts,
    )
    print(f"[TM] Collection completed partition={partition} counts={counts}")


def resolve_transfermarkt_from_existing(
    root: Path,
    partition: str,
    *,
    skip_api_backfill: bool = False,
    tm_db_url: str | None = None,
) -> None:
    """
    Re-resolve values from existing local files only:
    - uses existing tournament_squads.json
    - re-runs DB attach with latest matcher
    - applies API backfill (optional)
    No Wikipedia recollection is performed.
    """
    paths = resolve_collection_paths(root, partition)
    tournaments = tournaments_for_partition(partition)
    tournament_ids = [t.tournament_id for t in tournaments]
    mv_paths = squad_paths(paths.market_value_dir)
    mv_paths["duckdb"] = paths.tm_db_path
    _maybe_update_tm_db(paths.tm_db_path, tm_db_url, force=False)

    if not mv_paths["squads"].exists():
        raise FileNotFoundError(
            f"Missing {mv_paths['squads']}. Run collect-transfermarkt first to create squads."
        )
    squads_payload = json.loads(mv_paths["squads"].read_text(encoding="utf-8"))
    if not mv_paths["duckdb"].exists():
        raise FileNotFoundError(
            f"Missing DuckDB database: {mv_paths['duckdb']}. "
            "Run update-tm-db or provide --tm-db-url."
        )
    print(
        f"[TM] Resolving from existing squads partition={partition} "
        f"tournaments={squads_payload.get('tournament_count')} players={squads_payload.get('player_count')}"
    )
    start_dates = load_tournament_start_dates(paths.fixtures_path)
    conn = duckdb.connect(str(mv_paths["duckdb"]), read_only=True)
    try:
        enriched, unmatched = attach_market_values(
            squads_payload,
            conn=conn,
            start_dates=start_dates,
        )
    finally:
        conn.close()

    _write_json(mv_paths["with_value"], enriched)
    _write_json(mv_paths["unmatched"], unmatched)
    counts: dict[str, int] = {
        "squads_players": int(squads_payload.get("player_count", 0)),
        "valued_players": int(enriched.get("market_value_summary", {}).get("valued_players", 0)),
        "unmatched_players": int(unmatched.get("summary", {}).get("unmatched_players", 0)),
    }
    if not skip_api_backfill:
        backfill_counts = backfill_missing_from_api(mv_paths["with_value"], mv_paths["unmatched"])
        counts.update(backfill_counts)
    else:
        print("[TM] API backfill skipped by flag")

    write_manifest(
        paths.manifest_path,
        stage="resolve_transfermarkt_from_existing",
        partition=partition,
        tournament_ids=tournament_ids,
        counts=counts,
    )
    print(f"[TM] Resolve-from-existing completed partition={partition} counts={counts}")
