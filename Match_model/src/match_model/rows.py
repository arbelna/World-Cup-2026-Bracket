from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

CORE7_FEATURE_NAMES: tuple[str, ...] = (
    "elo_diff",
    "stage_binary",
    "host_diff",
    "team_a_confederation_idx",
    "team_b_confederation_idx",
    "z_log_top_15_average_value_team_a",
    "z_log_top_15_average_value_team_b",
)
FEATURE_INDEX: dict[str, int] = {
    name: idx for idx, name in enumerate(CORE7_FEATURE_NAMES)
}


@dataclass(slots=True)
class MatchRow:
    match_id: str
    competition: str
    team_a: str
    team_b: str
    is_mirror: bool
    elo_diff: float
    stage: str
    stage_binary: float
    host_diff: float
    team_a_confederation_idx: float
    team_b_confederation_idx: float
    z_log_top_15_average_value_team_a: float
    z_log_top_15_average_value_team_b: float
    y_soft: np.ndarray
    odds: list[list[float]] | None

    def feature_vector(self, feature_names: tuple[str, ...] = CORE7_FEATURE_NAMES) -> np.ndarray:
        full = np.array(
            [
                self.elo_diff,
                self.stage_binary,
                self.host_diff,
                self.team_a_confederation_idx,
                self.team_b_confederation_idx,
                self.z_log_top_15_average_value_team_a,
                self.z_log_top_15_average_value_team_b,
            ],
            dtype=float,
        )
        if feature_names == CORE7_FEATURE_NAMES:
            return full
        return np.array([full[FEATURE_INDEX[name]] for name in feature_names], dtype=float)

    def mirror(self) -> MatchRow:
        y = self.y_soft
        mirrored_y = np.array([y[2], y[1], y[0]], dtype=float)
        mirrored_odds = None
        if self.odds:
            mirrored_odds = [[row[2], row[1], row[0]] for row in self.odds]
        return MatchRow(
            match_id=f"{self.match_id}__mirror",
            competition=self.competition,
            team_a=self.team_b,
            team_b=self.team_a,
            is_mirror=True,
            elo_diff=-self.elo_diff,
            stage=self.stage,
            stage_binary=self.stage_binary,
            host_diff=-self.host_diff,
            team_a_confederation_idx=self.team_b_confederation_idx,
            team_b_confederation_idx=self.team_a_confederation_idx,
            z_log_top_15_average_value_team_a=self.z_log_top_15_average_value_team_b,
            z_log_top_15_average_value_team_b=self.z_log_top_15_average_value_team_a,
            y_soft=mirrored_y,
            odds=mirrored_odds,
        )


def build_row_from_dataset(match: dict[str, Any]) -> MatchRow | None:
    target = match.get("target_soft")
    if target is None:
        return None
    y_soft = np.asarray(target, dtype=float)
    stage = str(match.get("stage") or "")
    stage_bucket = "group" if stage == "group" else "knockout"

    return MatchRow(
        match_id=str(match["match_id"]),
        competition=str(match.get("competition", "")),
        team_a=str(match.get("team_a", "")),
        team_b=str(match.get("team_b", "")),
        is_mirror=False,
        elo_diff=float(match["elo_diff"]),
        stage=stage_bucket,
        stage_binary=float(match.get("stage_binary", 0.0)),
        host_diff=float(match.get("host_diff", 0.0)),
        team_a_confederation_idx=float(match.get("team_a_confederation_idx", -1.0)),
        team_b_confederation_idx=float(match.get("team_b_confederation_idx", -1.0)),
        z_log_top_15_average_value_team_a=float(
            match.get("z_log_top_15_average_value_team_a") or 0.0
        ),
        z_log_top_15_average_value_team_b=float(
            match.get("z_log_top_15_average_value_team_b") or 0.0
        ),
        y_soft=y_soft,
        odds=list(match.get("odds") or []) or None,
    )


def build_rows_with_mirrors(matches: list[dict[str, Any]]) -> list[MatchRow]:
    rows: list[MatchRow] = []
    for match in matches:
        canonical = build_row_from_dataset(match)
        if canonical is None:
            continue
        rows.append(canonical)
        rows.append(canonical.mirror())
    return rows
