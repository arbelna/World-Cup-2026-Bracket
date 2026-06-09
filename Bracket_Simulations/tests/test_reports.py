from __future__ import annotations

from pathlib import Path


def test_root_results_matches_output_mirror():
    stage_root = Path(__file__).resolve().parents[1]
    root_results = stage_root / "results.md"
    mirror_results = stage_root / "data" / "output" / "simulations" / "stage_prediction_backtest.md"

    assert root_results.exists()
    assert mirror_results.exists()
    root_text = root_results.read_text(encoding="utf-8")
    mirror_text = mirror_results.read_text(encoding="utf-8")

    assert "# Bracket_Simulations - historical backtest summary" in root_text
    assert "detailed generated report lives in `data/output/simulations/stage_prediction_backtest.md`" in root_text
    assert "## M5 all-team binary Brier" in root_text
    assert "## M6 all-team binary log loss" in root_text
    assert "## Monte Carlo standard error" in root_text
    assert "# Stage prediction backtest" in mirror_text
    assert "For the concise human-facing summary" in mirror_text
    assert "## Calibration -- reliability tables" in mirror_text
    assert "## Monte Carlo standard error" in mirror_text
    assert root_text != mirror_text
