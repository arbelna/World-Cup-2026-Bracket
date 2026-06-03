from __future__ import annotations

import csv
from pathlib import Path


class ModelProbabilityProvider:
    """Symmetric lookup of model 1X2 probs for any team pair."""

    def __init__(self, rows: list[dict[str, str | float]]) -> None:
        self._by_pair: dict[tuple[str, str], tuple[float, float, float]] = {}
        for row in rows:
            a = str(row["team_a"])
            b = str(row["team_b"])
            pa, pd, pb = float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"])
            self._by_pair[(a, b)] = (pa, pd, pb)
            self._by_pair[(b, a)] = (pb, pd, pa)

    @classmethod
    def from_csv(cls, path: Path) -> ModelProbabilityProvider:
        with path.open(encoding="utf-8", newline="") as f:
            return cls(list(csv.DictReader(f)))

    def get(self, team_a: str, team_b: str) -> tuple[float, float, float]:
        key = (team_a, team_b)
        if key not in self._by_pair:
            raise KeyError(f"No model probs for {team_a} vs {team_b}")
        return self._by_pair[key]
