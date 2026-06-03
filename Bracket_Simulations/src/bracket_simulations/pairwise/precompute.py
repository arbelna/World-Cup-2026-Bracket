from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bracket_simulations.config import TournamentConfig, load_tournament_config
from bracket_simulations.pairwise.metrics import normalize_probs
from bracket_simulations.pairwise.model_catboost import fit_predict
from bracket_simulations.pairwise.rows import MatchRow, build_rows_with_mirrors
from bracket_simulations.utils.matching import normalize_team_name


@dataclass(slots=True)
class TeamFeatures:
    z_log: float
    conf_idx: float
    elo: float
    competition: str


def _team_elo_from_row(row: dict, team: str) -> float:
    diff = float(row["elo_diff"])
    if str(row["team_a"]) == team:
        return diff / 2.0
    if str(row["team_b"]) == team:
        return -diff / 2.0
    raise KeyError(f"{team} not in match row")


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


def _build_team_features(dataset_path: Path, competition: str) -> dict[str, TeamFeatures]:
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    competition_rows = [row for row in rows if row.get("competition") == competition]
    feats: dict[str, TeamFeatures] = {}
    if not competition_rows:
        return feats

    # Reconstruct stable team Elo values from all pairwise elo_diff constraints:
    # elo(team_a) - elo(team_b) = elo_diff.
    teams = sorted(
        {
            str(row["team_a"])
            for row in competition_rows
        }
        | {
            str(row["team_b"])
            for row in competition_rows
        }
    )
    team_to_idx = {team: idx for idx, team in enumerate(teams)}
    a_mat = np.zeros((len(competition_rows), len(teams)), dtype=float)
    b_vec = np.zeros(len(competition_rows), dtype=float)
    for i, row in enumerate(competition_rows):
        a = str(row["team_a"])
        b = str(row["team_b"])
        a_mat[i, team_to_idx[a]] = 1.0
        a_mat[i, team_to_idx[b]] = -1.0
        b_vec[i] = float(row["elo_diff"])
    elo_solution, *_ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
    elo_by_team = {team: float(elo_solution[idx]) for team, idx in team_to_idx.items()}

    # z_log/confederation features are team-level constants in this dataset.
    # Keep first seen value per team for those fields.
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
        feats[team] = TeamFeatures(
            z_log=float(z_log),
            conf_idx=float(conf_idx),
            elo=elo_by_team[team],
            competition=competition,
        )
    return feats


def _build_pair_row(team_a: str, team_b: str, team_feats: dict[str, TeamFeatures]) -> MatchRow:
    fa = team_feats[team_a]
    fb = team_feats[team_b]
    return MatchRow(
        match_id=f"sim__{normalize_team_name(team_a)}__{normalize_team_name(team_b)}",
        competition=fa.competition,
        team_a=team_a,
        team_b=team_b,
        is_mirror=False,
        elo_diff=float(fa.elo - fb.elo),
        stage_binary=0.0,
        host_diff=0.0,
        team_a_confederation_idx=fa.conf_idx,
        team_b_confederation_idx=fb.conf_idx,
        z_log_top_15_average_value_team_a=fa.z_log,
        z_log_top_15_average_value_team_b=fb.z_log,
        y_soft=np.array([1 / 3, 1 / 3, 1 / 3], dtype=float),
    )


def precompute_for_config(config_name: str) -> Path:
    cfg = load_tournament_config(config_name)
    dataset_path = cfg.train_dataset
    all_rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    train_matches = all_rows
    if cfg.exclude_tournament_from_train:
        train_matches = [m for m in all_rows if m.get("tournament_id") != cfg.exclude_tournament_from_train]

    groups = json.loads(cfg.groups_file.read_text(encoding="utf-8"))["groups"]
    teams = sorted({t for ts in groups.values() for t in ts})
    team_feats = _build_team_features(dataset_path, cfg.match_dataset_filter_competition)
    missing = [t for t in teams if t not in team_feats]
    if missing:
        raise KeyError(f"Missing team features for: {missing}")

    train_rows = build_rows_with_mirrors(train_matches)
    pairs = list(itertools.combinations(teams, 2))
    test_rows = [_build_pair_row(a, b, team_feats) for a, b in pairs]
    mirror_rows = [r.mirror() for r in test_rows]

    probs = fit_predict(train_rows, test_rows, random_state=42)
    probs_mirror = fit_predict(train_rows, mirror_rows, random_state=42)
    probs_sym = normalize_probs(
        0.5
        * (
            probs
            + np.column_stack((probs_mirror[:, 2], probs_mirror[:, 1], probs_mirror[:, 0]))
        )
    )

    out_path = cfg.pairwise_predictions_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["team_a", "team_b", "pred_a", "pred_draw", "pred_b"])
        for (a, b), p in zip(pairs, probs_sym):
            writer.writerow([a, b, f"{p[0]:.8f}", f"{p[1]:.8f}", f"{p[2]:.8f}"])

    print(f"{config_name}: wrote {len(pairs)} pairs to {out_path}")
    return out_path
