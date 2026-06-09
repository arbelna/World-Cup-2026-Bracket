from __future__ import annotations

import sys
from pathlib import Path

import pytest

STAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bracket_simulations.prediction_backtest import (
    HISTORICAL_TOURNAMENTS,
    _cumulative_at_actual,
    aggregate_with_uncertainty,
    build_report,
)
from bracket_simulations.prediction_backtest_report import NOT_OBSERVED_CUMULATIVE_FREQUENCY


def test_cumulative_at_actual_not_observed_uses_sentinel():
    state = {
        "total_sims": 100,
        "config_counts": {
            "R16|||Argentina|Brazil|Chile|Mexico": 60,
            "R16|||France|Germany|Italy|Spain": 40,
        },
    }
    actual = ("Japan", "Netherlands", "Portugal", "Uruguay")
    result = _cumulative_at_actual(state, "R16", actual)

    assert result["rank_actual"] == 3
    assert result["p_joint_actual"] == 0.0
    assert result["cumulative_frequency"] == NOT_OBSERVED_CUMULATIVE_FREQUENCY
    assert result["joint_actual_observed"] is False


def test_cumulative_at_actual_observed_uses_empirical_cumulative():
    state = {
        "total_sims": 100,
        "config_counts": {
            "R16|||Argentina|Brazil|Chile|Mexico": 60,
            "R16|||France|Germany|Italy|Spain": 40,
        },
    }
    actual = ("Argentina", "Brazil", "Chile", "Mexico")
    result = _cumulative_at_actual(state, "R16", actual)

    assert result["rank_actual"] == 1
    assert result["p_joint_actual"] == 0.6
    assert result["cumulative_frequency"] == 0.6
    assert result["joint_actual_observed"] is True


@pytest.mark.integration
def test_build_report_contains_uncertainty_and_calibration_sections():
    """Smoke test: build_report runs and the rendered markdown has new sections."""
    rows, md, uncertainty, calibration, mcse = build_report(HISTORICAL_TOURNAMENTS)
    assert "Uncertainty" in md or "uncertainty" in md
    assert "Calibration" in md or "calibration" in md
    assert "Monte Carlo standard error" in md
    assert isinstance(mcse, dict)


@pytest.mark.integration
def test_aggregate_with_uncertainty_shape():
    """aggregate_with_uncertainty returns expected keys for all stages."""
    from bracket_simulations.actual_results import STAGES

    rows, _md, _unc, _cal, _mcse = build_report(HISTORICAL_TOURNAMENTS)
    uncertainty = aggregate_with_uncertainty(rows)
    for stage in STAGES:
        assert stage in uncertainty
        for metric in ("recall", "brier", "logloss"):
            assert metric in uncertainty[stage]
            u = uncertainty[stage][metric]
            assert "delta_mean" in u
            assert "ci_low" in u
            assert "ci_high" in u
            assert u["n_tournaments"] == len(HISTORICAL_TOURNAMENTS)
