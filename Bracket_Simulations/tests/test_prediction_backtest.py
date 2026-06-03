from __future__ import annotations

from bracket_simulations.prediction_backtest import _cumulative_at_actual
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
