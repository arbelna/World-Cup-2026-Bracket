from __future__ import annotations

import math

import pytest

from bracket_simulations.actual_results import STAGES
from bracket_simulations.calibration import BIN_EDGES, _wilson, collect_reliability_pairs_by_stage, reliability_table


def test_wilson_empty_bin():
    lo, hi = _wilson(0, 0)
    assert lo == 0.0
    assert hi == 0.0


def test_wilson_basic():
    lo, hi = _wilson(50, 100)
    assert 0.0 <= lo <= 0.5
    assert 0.5 <= hi <= 1.0
    assert lo < hi


def test_perfectly_calibrated():
    """For each bin midpoint p, generate enough pairs so observed approx p -> every gap approx 0 and ECE approx 0."""
    pairs: list[tuple[float, int]] = []
    for lo, hi in zip(BIN_EDGES[:-1], BIN_EDGES[1:]):
        p = (lo + min(hi, 1.0)) / 2
        n = 1000
        k = round(p * n)
        pairs.extend([(p, 1)] * k)
        pairs.extend([(p, 0)] * (n - k))

    rows, ece = reliability_table(pairs, BIN_EDGES)
    assert len(rows) > 0
    for row in rows:
        assert abs(row["gap"]) < 0.05, f"Gap too large for bin {row['lo']}-{row['hi']}: {row['gap']}"
    assert ece < 0.05


def test_all_overconfident():
    """p = 0.9, y = 0 everywhere -> large positive gap, ECE approx 0.9."""
    pairs = [(0.95, 0)] * 200  # falls in 0.9-1.01 bin
    rows, ece = reliability_table(pairs, BIN_EDGES)
    assert len(rows) == 1
    assert rows[0]["gap"] == pytest.approx(0.95, abs=1e-9)
    assert ece == pytest.approx(0.95, abs=1e-9)


def test_empty_bin_skipped():
    """Bins with no data should not appear in output."""
    pairs = [(0.05, 0)] * 10 + [(0.05, 1)] * 10  # only 0.0-0.1 bin populated
    rows, ece = reliability_table(pairs, BIN_EDGES)
    assert all(row["lo"] == 0.0 for row in rows)
    assert len(rows) == 1


def test_ece_nan_on_empty():
    rows, ece = reliability_table([], BIN_EDGES)
    assert len(rows) == 0
    assert math.isnan(ece)


def test_collect_reliability_pairs_by_stage_structure():
    """collect_reliability_pairs_by_stage returns a dict keyed by every STAGE."""
    from unittest.mock import patch

    fake_preds = {
        "TeamA": {f"p_at_least_{s}": "0.8" for s in STAGES},
        "TeamB": {f"p_at_least_{s}": "0.2" for s in STAGES},
    }

    class FakeActual:
        actual_at_least = {s: {"TeamA"} for s in STAGES}

    with (
        patch("bracket_simulations.calibration.build_actual_outcome", return_value=FakeActual()),
        patch("bracket_simulations.calibration._load_preds", return_value=fake_preds),
        patch("bracket_simulations.calibration.probabilities_csv", return_value="dummy.csv"),
    ):
        result = collect_reliability_pairs_by_stage(["wc2022"], "market_all")

    assert set(result.keys()) == set(STAGES)
    for stage, pairs in result.items():
        # 2 teams x 1 tournament = 2 pairs per stage
        assert len(pairs) == 2
        assert all(isinstance(p, float) and y in (0, 1) for p, y in pairs)


def test_by_stage_does_not_mix_base_rates():
    """Each stage's pairs should be independent of other stages."""
    from unittest.mock import patch

    fake_preds = {
        "TeamA": {f"p_at_least_{s}": "0.9" for s in STAGES},
        "TeamB": {f"p_at_least_{s}": "0.1" for s in STAGES},
    }

    class FakeActual:
        actual_at_least = {
            "R16": {"TeamA"},
            "QF": set(),
            "SF": set(),
            "final": set(),
            "winner": set(),
        }

    with (
        patch("bracket_simulations.calibration.build_actual_outcome", return_value=FakeActual()),
        patch("bracket_simulations.calibration._load_preds", return_value=fake_preds),
        patch("bracket_simulations.calibration.probabilities_csv", return_value="dummy.csv"),
    ):
        result = collect_reliability_pairs_by_stage(["wc2022"], "model_all")

    # R16: TeamA outcome=1, TeamB outcome=0
    r16_outcomes = {p: y for p, y in result["R16"]}
    assert r16_outcomes[0.9] == 1
    assert r16_outcomes[0.1] == 0

    # winner: both outcome=0
    winner_outcomes = [y for _, y in result["winner"]]
    assert all(y == 0 for y in winner_outcomes)
