from __future__ import annotations

import sys
from pathlib import Path

import pytest

STAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bracket_simulations.actual_results import build_actual_outcome


@pytest.fixture(scope="module")
def require_inputs():
    fixtures = STAGE_ROOT / "data" / "input" / "fixtures_stats.json"
    groups = STAGE_ROOT / "data" / "input" / "wc2022_groups.json"
    if not fixtures.exists() or not groups.exists():
        pytest.skip("Run sync-inputs and build-data first")


def test_wc2022_actual_qf_set(require_inputs):
    actual = build_actual_outcome("wc2022")
    qf = set(actual.actual_config["QF"])
    expected = {
        "Netherlands",
        "Argentina",
        "Croatia",
        "Brazil",
        "England",
        "France",
        "Morocco",
        "Portugal",
    }
    assert qf == expected
    assert actual.champion == "Argentina"
