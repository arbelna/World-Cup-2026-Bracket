from __future__ import annotations

import csv
from pathlib import Path


class ModelGroupProbabilityProvider:
    """Lookup symmetric model 1X2 probabilities for scheduled group fixtures."""

    def __init__(self, rows: list[dict[str, str | float]]) -> None:
        self._by_pair: dict[tuple[str, str], tuple[float, float, float]] = {}
        for row in rows:
            a = str(row["team_a"])
            b = str(row["team_b"])
            pa, pd, pb = float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"])
            self._by_pair[(a, b)] = (pa, pd, pb)
            self._by_pair[(b, a)] = (pb, pd, pa)

    @classmethod
    def from_csv(cls, path: Path) -> ModelGroupProbabilityProvider:
        with path.open(encoding="utf-8", newline="") as f:
            return cls(list(csv.DictReader(f)))

    def get(
        self,
        team_a: str,
        team_b: str,
        *,
        stage: str | None = None,
        slot_id: str | None = None,
    ) -> tuple[float, float, float]:
        _ = stage, slot_id
        key = (team_a, team_b)
        if key not in self._by_pair:
            raise KeyError(f"No model group probs for {team_a} vs {team_b}")
        return self._by_pair[key]


class ModelKnockoutProbabilityProvider:
    """Lookup symmetric model 1X2 probabilities keyed by knockout stage and slot."""

    def __init__(self, rows: list[dict[str, str | float]]) -> None:
        self._by_context: dict[tuple[str, str, str, str], tuple[float, float, float]] = {}
        self._stage_pair_values: dict[tuple[str, str, str], list[tuple[float, float, float]]] = {}
        for row in rows:
            stage = str(row["stage"])
            slot_id = str(row["slot_id"])
            a = str(row["team_a"])
            b = str(row["team_b"])
            pa, pd, pb = float(row["pred_a"]), float(row["pred_draw"]), float(row["pred_b"])
            self._by_context[(stage, slot_id, a, b)] = (pa, pd, pb)
            self._by_context[(stage, slot_id, b, a)] = (pb, pd, pa)
            self._stage_pair_values.setdefault((stage, a, b), []).append((pa, pd, pb))
            self._stage_pair_values.setdefault((stage, b, a), []).append((pb, pd, pa))

    @classmethod
    def from_csv(cls, path: Path) -> ModelKnockoutProbabilityProvider:
        with path.open(encoding="utf-8", newline="") as f:
            return cls(list(csv.DictReader(f)))

    def get(
        self,
        team_a: str,
        team_b: str,
        *,
        stage: str | None = None,
        slot_id: str | None = None,
    ) -> tuple[float, float, float]:
        if stage is not None and slot_id is None:
            values = self._stage_pair_values.get((stage, team_a, team_b))
            if not values:
                raise KeyError(
                    f"No model knockout probs for stage={stage} {team_a} vs {team_b}"
                )
            n = float(len(values))
            pa = sum(value[0] for value in values) / n
            pd = sum(value[1] for value in values) / n
            pb = sum(value[2] for value in values) / n
            return pa, pd, pb
        if stage is None or slot_id is None:
            raise KeyError(
                f"Knockout model lookup requires stage and slot_id for {team_a} vs {team_b}"
            )
        key = (stage, str(slot_id), team_a, team_b)
        if key not in self._by_context:
            raise KeyError(
                f"No model knockout probs for stage={stage} slot_id={slot_id} {team_a} vs {team_b}"
            )
        return self._by_context[key]


class ModelProbabilityProvider(ModelGroupProbabilityProvider):
    """Backward-compatible alias for the group-stage provider."""
