from __future__ import annotations

import math

import pytest

from bracket_simulations.calibration import BIN_EDGES, _wilson, reliability_table


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
    """For each bin midpoint p, generate enough pairs so observed ≈ p -> every gap ≈ 0 and ECE ≈ 0."""
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
    """p = 0.9, y = 0 everywhere -> large positive gap, ECE ≈ 0.9."""
    pairs = [(0.95, 0)] * 200  # falls in 0.9–1.01 bin
    rows, ece = reliability_table(pairs, BIN_EDGES)
    assert len(rows) == 1
    assert rows[0]["gap"] == pytest.approx(0.95, abs=1e-9)
    assert ece == pytest.approx(0.95, abs=1e-9)


def test_empty_bin_skipped():
    """Bins with no data should not appear in output."""
    pairs = [(0.05, 0)] * 10 + [(0.05, 1)] * 10  # only 0.0–0.1 bin populated
    rows, ece = reliability_table(pairs, BIN_EDGES)
    assert all(row["lo"] == 0.0 for row in rows)
    assert len(rows) == 1


def test_ece_nan_on_empty():
    rows, ece = reliability_table([], BIN_EDGES)
    assert len(rows) == 0
    assert math.isnan(ece)
