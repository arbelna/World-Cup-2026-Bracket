from __future__ import annotations

import pytest

from bracket_simulations.uncertainty import block_bootstrap_delta


def test_perfectly_separated_model_better():
    """Model always +0.5 better -> CI entirely above 0, significant."""
    model = [0.8, 0.9, 0.7, 0.85]
    market = [0.3, 0.4, 0.2, 0.35]
    result = block_bootstrap_delta(model, market)
    assert result["ci_low"] > 0
    assert result["significant"] is True
    assert result["delta_mean"] == pytest.approx(0.5, abs=1e-9)


def test_symmetric_noise_not_significant():
    """Model vs market alternates sign -> CI contains 0, not significant."""
    model = [0.6, 0.4, 0.6, 0.4]
    market = [0.4, 0.6, 0.4, 0.6]
    result = block_bootstrap_delta(model, market)
    assert result["ci_low"] <= 0 <= result["ci_high"]
    assert result["significant"] is False


def test_n_model_better_plus_market_better_leq_n_tournaments():
    model = [0.7, 0.3, 0.5, 0.8]
    market = [0.4, 0.6, 0.5, 0.2]
    result = block_bootstrap_delta(model, market)
    n = result["n_tournaments"]
    assert result["n_model_better"] + result["n_market_better"] <= n


def test_output_keys():
    result = block_bootstrap_delta([0.5, 0.5], [0.4, 0.4])
    assert set(result.keys()) == {
        "delta_mean", "ci_low", "ci_high",
        "n_tournaments", "n_model_better", "n_market_better", "significant",
    }


def test_market_consistently_better():
    """Market always better -> CI entirely below 0, significant."""
    model = [0.2, 0.1, 0.3, 0.15]
    market = [0.7, 0.8, 0.6, 0.75]
    result = block_bootstrap_delta(model, market)
    assert result["ci_high"] < 0
    assert result["significant"] is True
