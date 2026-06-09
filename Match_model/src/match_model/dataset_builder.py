from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from match_model.form_features import confederation_index, host_diff
from match_model.parsers.old_stats_parser import OldStatsMatch, parse_all_old_stats
from match_model.targets import target_from_match
from match_model.utils.matching import (
    normalize_date,
    normalize_team_name,
    normalized_team_pair,
)

TOP_N_GROUPS = (1, 3, 5, 10, 15)
VALUE_AGGREGATES = ("total", "average", "median")

MATCH_DETAIL_FIELDS = (
    "match_id",
    "tournament_id",
    "competition",
    "date",
    "team_a",
    "team_b",
    "stage",
    "venue",
)

CORE7_FEATURE_FIELDS = (
    "elo_diff",
    "stage_binary",
    "host_diff",
    "team_a_confederation_idx",
    "team_b_confederation_idx",
    "z_log_top_15_average_value_team_a",
    "z_log_top_15_average_value_team_b",
)

TARGET_FIELDS = ("odds", "target_soft")

ROW_FIELD_ORDER = MATCH_DETAIL_FIELDS + CORE7_FEATURE_FIELDS + TARGET_FIELDS

TEAM_MARKET_VALUE_ALIASES: dict[str, str] = {
    "czechia": "czechrepublic",
    "drepublicofcongo": "drcongo",
    "drcongo": "drcongo",
}


def build_dataset_match_id(tournament_id: str, team_a: str, team_b: str, date_value: str) -> str:
    return (
        f"md__{tournament_id}__{normalize_team_name(team_a)}__"
        f"{normalize_team_name(team_b)}__{date_value}"
    )


def _fixture_date(fixture: dict[str, Any]) -> str:
    return normalize_date(str(fixture.get("date_utc")))


def _load_old_stats_index(old_stats_dir: Path):
    matches = parse_all_old_stats(old_stats_dir)
    index: dict[tuple[str, tuple[str, str], str], list[OldStatsMatch]] = defaultdict(list)
    for match in matches:
        pair = normalized_team_pair(match.team1, match.team2)
        index[(match.tournament_id, pair, match.date)].append(match)
    return index, OldStatsMatch


def _find_old_stats_match(
    fixture: dict[str, Any],
    old_stats_index: dict,
    OldStatsMatch: type,
    max_day_delta: int = 1,
) -> tuple[Any | None, list[str]]:
    warnings: list[str] = []
    tournament_id = str(fixture["tournament_id"])
    pair = normalized_team_pair(str(fixture["home_team"]), str(fixture["away_team"]))
    fixture_day = _fixture_date(fixture)
    try:
        target_date = datetime.fromisoformat(fixture_day).date()
    except ValueError:
        return None, ["invalid_fixture_date"]

    exact = old_stats_index.get((tournament_id, pair, fixture_day), [])
    if len(exact) == 1:
        return exact[0], warnings
    if len(exact) > 1:
        warnings.append(f"ambiguous_old_stats_join: {tournament_id} {fixture_day}")
        return exact[0], warnings

    nearby: list[tuple[int, Any]] = []
    for (tid, indexed_pair, match_day), candidates in old_stats_index.items():
        if tid != tournament_id or indexed_pair != pair:
            continue
        try:
            delta = abs((datetime.fromisoformat(match_day).date() - target_date).days)
        except ValueError:
            continue
        if delta <= max_day_delta:
            for candidate in candidates:
                nearby.append((delta, candidate))

    if not nearby:
        return None, warnings
    nearby.sort(key=lambda item: item[0])
    return nearby[0][1], warnings


def _remap_old_stats_stage(
    old_match: Any,
    team_a: str,
    team_b: str,
) -> str | None:
    return str(old_match.stage) if old_match is not None else None


def _infer_stage_without_old_stats(fixture: dict[str, Any]) -> str | None:
    tournament_id = str(fixture.get("tournament_id", ""))
    # WC2026 fixtures in this repo are pre-tournament group-stage schedule rows.
    if tournament_id == "world-cup-2026":
        return "group"
    return None


def _aggregate_odds(
    fixture: dict[str, Any],
    odds_rows: list[dict[str, Any]],
) -> list[list[float]]:
    team_a = str(fixture["home_team"])
    triples: list[list[float]] = []
    for row in odds_rows:
        home_odds = float(row["home_odds"])
        draw_odds = float(row["draw_odds"])
        away_odds = float(row["away_odds"])
        if normalize_team_name(str(row.get("home_team", ""))) == normalize_team_name(team_a):
            triple = (home_odds, draw_odds, away_odds)
        else:
            triple = (away_odds, draw_odds, home_odds)
        triples.append([triple[0], triple[1], triple[2]])
    return triples


def _load_confederation_map(collection_dir: Path) -> dict[str, str]:
    path = collection_dir / "team_confederations.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload.get("teams", {}))


def _resolve_team_ratings_path(collection_dir: Path) -> Path:
    for filename in ("team_ratings.json", "teams_ratings.json"):
        path = collection_dir / filename
        if path.exists():
            return path
    raise FileNotFoundError(f"Missing team ratings file in {collection_dir}")


def _load_team_ratings_index(collection_dir: Path) -> dict[tuple[str, str], int]:
    path = _resolve_team_ratings_path(collection_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"team ratings file must be a list: {path}")

    index: dict[tuple[str, str], int] = {}
    for row in payload:
        tournament_id = str(row.get("tournament_id", "")).strip()
        team_name = str(row.get("team_name", "")).strip()
        elo_rating = row.get("elo_rating")
        if not tournament_id or not team_name or elo_rating is None:
            continue
        index[(tournament_id, normalize_team_name(team_name))] = int(elo_rating)
    return index


def _lookup_tournament_start_elo(
    ratings_index: dict[tuple[str, str], int],
    tournament_id: str,
    team_name: str,
) -> int | None:
    return ratings_index.get((tournament_id, normalize_team_name(team_name)))


def _lookup_confederation(teams: dict[str, str], name: str) -> str | None:
    if not name or not str(name).strip():
        return None
    text = str(name).strip()
    if text in teams:
        return teams[text]
    normalized = normalize_team_name(text)
    for canonical, confederation in teams.items():
        if normalize_team_name(canonical) == normalized:
            return confederation
    return None


def _team_market_value_metrics(players: list[dict[str, Any]]) -> dict[str, float | None]:
    values = sorted(
        [
            float(player["market_value"])
            for player in players
            if player.get("market_value") is not None
        ],
        reverse=True,
    )
    metrics: dict[str, float | None] = {}
    for top_n in TOP_N_GROUPS:
        selected = values[:top_n]
        if not selected:
            metrics[f"top_{top_n}_total_value"] = None
            metrics[f"top_{top_n}_average_value"] = None
            metrics[f"top_{top_n}_median_value"] = None
            continue
        metrics[f"top_{top_n}_total_value"] = float(sum(selected))
        metrics[f"top_{top_n}_average_value"] = float(sum(selected) / len(selected))
        mid = len(selected) // 2
        if len(selected) % 2 == 1:
            metrics[f"top_{top_n}_median_value"] = float(sorted(selected)[mid])
        else:
            s = sorted(selected)
            metrics[f"top_{top_n}_median_value"] = float((s[mid - 1] + s[mid]) / 2.0)
    return metrics


def _build_market_value_index(squads_payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, float | None]]:
    out: dict[tuple[str, str], dict[str, float | None]] = {}
    for tournament in squads_payload.get("tournaments", []):
        tournament_id = str(tournament.get("tournament_id", ""))
        if not tournament_id:
            continue
        for team in tournament.get("teams", []):
            team_name = str(team.get("team_name", ""))
            if not team_name:
                continue
            out[(tournament_id, normalize_team_name(team_name))] = _team_market_value_metrics(
                list(team.get("players", []))
            )
    for tournament_id in {key[0] for key in out}:
        for alias, target in TEAM_MARKET_VALUE_ALIASES.items():
            target_metrics = out.get((tournament_id, normalize_team_name(target)))
            if target_metrics is None:
                continue
            alias_norm = normalize_team_name(alias)
            if (tournament_id, alias_norm) not in out:
                out[(tournament_id, alias_norm)] = dict(target_metrics)
    return out


def _log_transform_metrics(metrics: dict[str, float | None]) -> dict[str, float | None]:
    out = dict(metrics)
    for top_n in TOP_N_GROUPS:
        for aggregate in VALUE_AGGREGATES:
            key = f"top_{top_n}_{aggregate}_value"
            value = metrics.get(key)
            out[f"log_top_{top_n}_{aggregate}_value"] = (
                None if value is None else float(math.log1p(max(0.0, value)))
            )
    return out


def _compute_tournament_norm_stats(
    team_value_index: dict[tuple[str, str], dict[str, float | None]],
) -> dict[str, dict[str, tuple[float, float]]]:
    by_tournament: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (tournament_id, _team_key), metrics in team_value_index.items():
        for metric_name, metric_value in metrics.items():
            if metric_value is not None:
                by_tournament[tournament_id][metric_name].append(float(metric_value))

    stats: dict[str, dict[str, tuple[float, float]]] = {}
    for tournament_id, metric_map in by_tournament.items():
        stats[tournament_id] = {}
        for metric_name, values in metric_map.items():
            if not values:
                continue
            mean = float(sum(values) / len(values))
            var = float(sum((v - mean) ** 2 for v in values) / len(values))
            stats[tournament_id][metric_name] = (mean, math.sqrt(var))
    return stats


def _apply_z_metrics(
    tournament_id: str,
    metrics: dict[str, float | None],
    norm_stats: dict[str, dict[str, tuple[float, float]]],
) -> dict[str, float | None]:
    out = dict(metrics)
    tournament_stats = norm_stats.get(tournament_id, {})
    for top_n in TOP_N_GROUPS:
        for aggregate in VALUE_AGGREGATES:
            log_key = f"log_top_{top_n}_{aggregate}_value"
            log_value = metrics.get(log_key)
            log_stats = tournament_stats.get(log_key)
            out[f"z_log_top_{top_n}_{aggregate}_value"] = (
                None
                if log_value is None or log_stats is None or log_stats[1] == 0.0
                else float((log_value - log_stats[0]) / log_stats[1])
            )
    return out


def _is_host_at_venue(team: str, venue_country: str | None) -> bool | None:
    if venue_country is None:
        return None
    return normalize_team_name(team) == normalize_team_name(venue_country)


def _project_row(
    *,
    match_id: str,
    tournament_id: str,
    competition: str,
    date_value: str,
    team_a: str,
    team_b: str,
    stage: str | None,
    venue: str | None,
    elo_diff: float | None,
    host_diff_value: float,
    conf_a_idx: float,
    conf_b_idx: float,
    z_a: float | None,
    z_b: float | None,
    odds: list[list[float]],
    target_soft: list[float] | None,
) -> dict[str, Any]:
    stage_str = str(stage) if stage else ""
    row = {
        "match_id": match_id,
        "tournament_id": tournament_id,
        "competition": competition,
        "date": date_value,
        "team_a": team_a,
        "team_b": team_b,
        "stage": stage_str,
        "venue": venue,
        "elo_diff": elo_diff,
        "stage_binary": 1.0 if stage_str == "group" else 0.0,
        "host_diff": host_diff_value,
        "team_a_confederation_idx": conf_a_idx,
        "team_b_confederation_idx": conf_b_idx,
        "z_log_top_15_average_value_team_a": z_a,
        "z_log_top_15_average_value_team_b": z_b,
        "odds": odds,
        "target_soft": target_soft,
    }
    return {key: row[key] for key in ROW_FIELD_ORDER}


def build_match_dataset(
    *,
    collection_dir: Path,
    old_stats_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fixtures_path = collection_dir / "fixtures_stats.json"
    odds_path = collection_dir / "matched_odds.json"
    squads_path = collection_dir / "tournament_squads_with_value.json"

    fixtures: list[dict[str, Any]] = json.loads(fixtures_path.read_text(encoding="utf-8"))
    odds_rows: list[dict[str, Any]] = json.loads(odds_path.read_text(encoding="utf-8"))
    squads_with_values = json.loads(squads_path.read_text(encoding="utf-8"))
    conf_teams = _load_confederation_map(collection_dir)
    ratings_index = _load_team_ratings_index(collection_dir)

    old_stats_index, OldStatsMatch = _load_old_stats_index(old_stats_dir)

    raw_mv_index = _build_market_value_index(squads_with_values)
    market_value_index = {
        key: _log_transform_metrics(metrics) for key, metrics in raw_mv_index.items()
    }
    market_value_norm_stats = _compute_tournament_norm_stats(market_value_index)

    odds_by_match_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in odds_rows:
        odds_by_match_id[str(row["match_id"])].append(row)

    dataset: list[dict[str, Any]] = []
    warnings: list[str] = []
    skipped_no_target = 0
    skipped_no_elo = 0
    skipped_no_stage = 0
    by_tournament: Counter[str] = Counter()

    for fixture in fixtures:
        team_a = str(fixture["home_team"])
        team_b = str(fixture["away_team"])
        date_value = _fixture_date(fixture)
        tournament_id = str(fixture["tournament_id"])
        competition = str(fixture.get("tournament_name") or fixture.get("competition", ""))

        elo_a = _lookup_tournament_start_elo(ratings_index, tournament_id, team_a)
        elo_b = _lookup_tournament_start_elo(ratings_index, tournament_id, team_b)
        if elo_a is None or elo_b is None:
            skipped_no_elo += 1
            warnings.append(
                f"missing_tournament_start_elo: {tournament_id} {date_value} {team_a} vs {team_b}"
            )
            continue
        elo_diff = float(elo_a - elo_b)

        old_match, join_warnings = _find_old_stats_match(fixture, old_stats_index, OldStatsMatch)
        warnings.extend(join_warnings)
        stage = _remap_old_stats_stage(old_match, team_a, team_b)
        if stage is None:
            inferred_stage = _infer_stage_without_old_stats(fixture)
            if inferred_stage is None:
                skipped_no_stage += 1
                warnings.append(
                    f"missing_old_stats_join: {tournament_id} {date_value} {team_a} vs {team_b}"
                )
                continue
            stage = inferred_stage
            warnings.append(
                f"inferred_stage_without_old_stats: {tournament_id} {date_value} {team_a} vs {team_b} -> {stage}"
            )

        fixture_match_id = str(fixture["match_id"])
        odds_list = _aggregate_odds(fixture, odds_by_match_id.get(fixture_match_id, []))
        if not odds_list:
            skipped_no_target += 1
            continue

        probe = {"odds": odds_list}
        target = target_from_match(probe)
        if target is None:
            skipped_no_target += 1
            continue

        venue_country = str(fixture.get("venue") or "").strip() or None
        conf_a = _lookup_confederation(conf_teams, team_a)
        conf_b = _lookup_confederation(conf_teams, team_b)

        team_a_mv = _apply_z_metrics(
            tournament_id,
            market_value_index.get((tournament_id, normalize_team_name(team_a)), {}),
            market_value_norm_stats,
        )
        team_b_mv = _apply_z_metrics(
            tournament_id,
            market_value_index.get((tournament_id, normalize_team_name(team_b)), {}),
            market_value_norm_stats,
        )

        row = _project_row(
            match_id=build_dataset_match_id(tournament_id, team_a, team_b, date_value),
            tournament_id=tournament_id,
            competition=competition,
            date_value=date_value,
            team_a=team_a,
            team_b=team_b,
            stage=stage,
            venue=venue_country,
            elo_diff=elo_diff,
            host_diff_value=host_diff(
                _is_host_at_venue(team_a, venue_country),
                _is_host_at_venue(team_b, venue_country),
            ),
            conf_a_idx=confederation_index(conf_a),
            conf_b_idx=confederation_index(conf_b),
            z_a=team_a_mv.get("z_log_top_15_average_value"),
            z_b=team_b_mv.get("z_log_top_15_average_value"),
            odds=odds_list,
            target_soft=target.tolist(),
        )
        dataset.append(row)
        by_tournament[competition] += 1

    match_ids = [str(item["match_id"]) for item in dataset]
    if len(match_ids) != len(set(match_ids)):
        raise ValueError("Duplicate dataset match_id values detected")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "track": "final_bracket_match_model",
        "field_order": list(ROW_FIELD_ORDER),
        "core7_features": list(CORE7_FEATURE_FIELDS),
        "feature_notes": {
            "elo_diff": "Tournament-start Elo difference from collection team_ratings/teams_ratings snapshots.",
        },
        "totals": {
            "fixtures": len(fixtures),
            "matches": len(dataset),
            "by_tournament": dict(sorted(by_tournament.items())),
            "skipped_no_elo": skipped_no_elo,
            "skipped_no_stage": skipped_no_stage,
            "skipped_no_target": skipped_no_target,
        },
        "warnings_sample": warnings[:50],
        "n_warnings": len(warnings),
    }
    return dataset, summary
