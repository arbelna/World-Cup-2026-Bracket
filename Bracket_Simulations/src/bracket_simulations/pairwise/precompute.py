from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bracket_simulations.config import load_tournament_config
from bracket_simulations.model_variants import resolve_model_variant, variant_pairwise_path
from bracket_simulations.pairwise.model_catboost import fit_predict
from bracket_simulations.pairwise.rows import MatchRow, build_rows_with_mirrors
from bracket_simulations.tournament_data import (
    host_diff_for_country,
    load_knockout_context,
    load_tournament_fixtures,
    load_tournament_team_ratings,
)
from bracket_simulations.utils.matching import normalize_team_name


@dataclass(slots=True)
class TeamFeatures:
    z_log: float
    conf_idx: float
    elo: float
    competition: str


def _team_z_from_row(row: dict, team: str) -> float:
    if str(row["team_a"]) == team:
        return float(row["z_log_top_15_average_value_team_a"])
    if str(row["team_b"]) == team:
        return float(row["z_log_top_15_average_value_team_b"])
    raise KeyError(f"{team} not in match row")


def _team_conf_from_row(row: dict, team: str) -> float:
    if str(row["team_a"]) == team:
        return float(row["team_a_confederation_idx"])
    if str(row["team_b"]) == team:
        return float(row["team_b_confederation_idx"])
    raise KeyError(f"{team} not in match row")


def _build_team_features(
    dataset_path: Path,
    competition: str,
    team_ratings_path: Path,
    tournament_id: str,
) -> dict[str, TeamFeatures]:
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    competition_rows = [row for row in rows if row.get("competition") == competition]
    feats: dict[str, TeamFeatures] = {}
    if not competition_rows:
        return feats

    elo_by_team = load_tournament_team_ratings(team_ratings_path, tournament_id)
    if not elo_by_team:
        raise KeyError(f"No tournament-start Elo ratings found for {tournament_id}")

    side_features: dict[str, tuple[float, float]] = {}
    for row in competition_rows:
        for team in (str(row["team_a"]), str(row["team_b"])):
            if team in side_features:
                continue
            side_features[team] = (
                _team_z_from_row(row, team),
                _team_conf_from_row(row, team),
            )

    for team, (z_log, conf_idx) in side_features.items():
        if team not in elo_by_team:
            continue
        feats[team] = TeamFeatures(
            z_log=float(z_log),
            conf_idx=float(conf_idx),
            elo=float(elo_by_team[team]),
            competition=competition,
        )
    return feats


def _build_pair_row(
    *,
    team_a: str,
    team_b: str,
    team_feats: dict[str, TeamFeatures],
    stage_binary: float,
    host_diff: float,
    match_id: str,
) -> MatchRow:
    fa = team_feats[team_a]
    fb = team_feats[team_b]
    return MatchRow(
        match_id=match_id,
        competition=fa.competition,
        team_a=team_a,
        team_b=team_b,
        is_mirror=False,
        elo_diff=float(fa.elo - fb.elo),
        stage_binary=stage_binary,
        host_diff=host_diff,
        team_a_confederation_idx=fa.conf_idx,
        team_b_confederation_idx=fb.conf_idx,
        z_log_top_15_average_value_team_a=fa.z_log,
        z_log_top_15_average_value_team_b=fb.z_log,
        y_soft=np.array([1 / 3, 1 / 3, 1 / 3], dtype=float),
    )


def _predict_rows(
    train_rows: list[MatchRow],
    test_rows: list[MatchRow],
    *,
    feature_names: tuple[str, ...],
) -> np.ndarray:
    if not test_rows:
        return np.zeros((0, 3), dtype=float)
    return fit_predict(train_rows, test_rows, feature_names=feature_names, random_state=42)


def _group_fixture_rows(
    *,
    fixtures: list[dict],
    groups: dict[str, list[str]],
    team_feats: dict[str, TeamFeatures],
) -> tuple[list[MatchRow], list[dict[str, str]]]:
    team_to_group = {
        normalize_team_name(team): group_label
        for group_label, teams in groups.items()
        for team in teams
    }
    seen_pairs: set[tuple[str, str]] = set()
    rows: list[MatchRow] = []
    meta: list[dict[str, str]] = []
    for fixture in sorted(fixtures, key=lambda row: str(row.get("date_utc", ""))):
        team_a = str(fixture.get("home_team", ""))
        team_b = str(fixture.get("away_team", ""))
        group_a = team_to_group.get(normalize_team_name(team_a))
        group_b = team_to_group.get(normalize_team_name(team_b))
        if not group_a or group_a != group_b:
            continue
        pair_key = tuple(sorted((normalize_team_name(team_a), normalize_team_name(team_b))))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        if team_a not in team_feats or team_b not in team_feats:
            continue
        venue = str(fixture.get("venue") or "").strip() or None
        rows.append(
            _build_pair_row(
                team_a=team_a,
                team_b=team_b,
                team_feats=team_feats,
                stage_binary=1.0,
                host_diff=host_diff_for_country(team_a, team_b, venue),
                match_id=str(fixture.get("match_id") or f"group__{normalize_team_name(team_a)}__{normalize_team_name(team_b)}"),
            )
        )
        meta.append(
            {
                "match_id": str(fixture.get("match_id") or ""),
                "group": group_a,
                "venue": venue or "",
            }
        )
    return rows, meta


def _iter_knockout_slots(bracket: dict) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []
    for match_def in bracket.get("r32", []):
        slots.append(("R32", str(match_def["id"])))
    for stage_key, stage_name in (("r16", "R16"), ("qf", "QF"), ("sf", "SF")):
        slots.extend((stage_name, str(idx + 1)) for idx, _ in enumerate(bracket.get(stage_key, [])))
    if bracket.get("final") is not None:
        slots.append(("final", "1"))
    if bracket.get("third_place") is not None:
        slots.append(("third_place", "1"))
    return slots


def _knockout_rows(
    *,
    teams: list[str],
    bracket: dict,
    knockout_context: dict[str, dict[str, str]],
    team_feats: dict[str, TeamFeatures],
) -> tuple[list[MatchRow], list[dict[str, str]]]:
    rows: list[MatchRow] = []
    meta: list[dict[str, str]] = []
    for stage, slot_id in _iter_knockout_slots(bracket):
        host_country = knockout_context.get(stage, {}).get(slot_id)
        if stage not in knockout_context or slot_id not in knockout_context[stage]:
            raise KeyError(f"Missing knockout host context for stage={stage} slot_id={slot_id}")
        for team_a, team_b in itertools.combinations(teams, 2):
            if team_a not in team_feats or team_b not in team_feats:
                continue
            rows.append(
                _build_pair_row(
                    team_a=team_a,
                    team_b=team_b,
                    team_feats=team_feats,
                    stage_binary=0.0,
                    host_diff=host_diff_for_country(team_a, team_b, host_country),
                    match_id=f"sim__{stage.lower()}__{slot_id}__{normalize_team_name(team_a)}__{normalize_team_name(team_b)}",
                )
            )
            meta.append(
                {
                    "stage": stage,
                    "slot_id": slot_id,
                    "host_country": host_country,
                }
            )
    return rows, meta


def _write_group_predictions(path: Path, rows: list[MatchRow], probs: np.ndarray, meta: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["match_id", "group", "venue", "team_a", "team_b", "pred_a", "pred_draw", "pred_b"])
        for row, p, info in zip(rows, probs, meta):
            writer.writerow(
                [
                    info["match_id"],
                    info["group"],
                    info["venue"],
                    row.team_a,
                    row.team_b,
                    f"{p[0]:.8f}",
                    f"{p[1]:.8f}",
                    f"{p[2]:.8f}",
                ]
            )


def _write_knockout_predictions(path: Path, rows: list[MatchRow], probs: np.ndarray, meta: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["stage", "slot_id", "host_country", "team_a", "team_b", "pred_a", "pred_draw", "pred_b"]
        )
        for row, p, info in zip(rows, probs, meta):
            writer.writerow(
                [
                    info["stage"],
                    info["slot_id"],
                    info["host_country"],
                    row.team_a,
                    row.team_b,
                    f"{p[0]:.8f}",
                    f"{p[1]:.8f}",
                    f"{p[2]:.8f}",
                ]
            )


def precompute_for_config(config_name: str, *, variant_id: str = "base") -> dict[str, Path]:
    cfg = load_tournament_config(config_name)
    variant = resolve_model_variant(variant_id=variant_id)
    dataset_path = cfg.train_dataset
    all_rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    train_matches = all_rows
    if cfg.exclude_tournament_from_train:
        train_matches = [m for m in all_rows if m.get("tournament_id") != cfg.exclude_tournament_from_train]

    groups = json.loads(cfg.groups_file.read_text(encoding="utf-8"))["groups"]
    teams = sorted({t for ts in groups.values() for t in ts})
    team_feats = _build_team_features(
        dataset_path,
        cfg.match_dataset_filter_competition,
        cfg.team_ratings_file,
        cfg.tournament_id,
    )
    missing = [t for t in teams if t not in team_feats]
    if missing:
        raise KeyError(f"Missing team features for: {missing}")

    train_rows = build_rows_with_mirrors(train_matches)
    fixtures = load_tournament_fixtures(cfg.fixtures_file, cfg.tournament_id)
    group_rows, group_meta = _group_fixture_rows(fixtures=fixtures, groups=groups, team_feats=team_feats)
    group_probs = _predict_rows(train_rows, group_rows, feature_names=variant.feature_names)
    group_path = variant_pairwise_path(cfg.group_pairwise_predictions_file, variant.variant_id)
    _write_group_predictions(group_path, group_rows, group_probs, group_meta)

    bracket = json.loads(cfg.knockout_bracket_file.read_text(encoding="utf-8"))
    knockout_context = load_knockout_context(cfg.knockout_context_file)
    knockout_rows, knockout_meta = _knockout_rows(
        teams=teams,
        bracket=bracket,
        knockout_context=knockout_context,
        team_feats=team_feats,
    )
    knockout_probs = _predict_rows(train_rows, knockout_rows, feature_names=variant.feature_names)
    knockout_path = variant_pairwise_path(cfg.knockout_pairwise_predictions_file, variant.variant_id)
    _write_knockout_predictions(
        knockout_path,
        knockout_rows,
        knockout_probs,
        knockout_meta,
    )

    print(
        f"{config_name}/{variant.variant_id}: wrote {len(group_rows)} group fixtures to {group_path}"
    )
    print(
        f"{config_name}/{variant.variant_id}: wrote {len(knockout_rows)} knockout slot-pair rows to "
        f"{knockout_path}"
    )
    return {
        "group": group_path,
        "knockout": knockout_path,
    }
