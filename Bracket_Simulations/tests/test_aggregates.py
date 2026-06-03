from __future__ import annotations

import pytest

from bracket_simulations.aggregates import merge_config_counts, merge_reach_counts, config_tuple_key
from bracket_simulations.probabilities.davidson import davidson_90min_probs, et_win_prob_team_a


def test_davidson_probs_sum_to_one():
    w_a, p_d, w_b = davidson_90min_probs(1.2, 0.9, 0.3)
    assert abs(w_a + p_d + w_b - 1.0) < 1e-9


def test_et_formula_symmetry():
    assert et_win_prob_team_a(0.4, 0.4) == pytest.approx(0.5)


def test_config_merge_idempotent():
    state = {"total_sims": 0, "reach_counts": {}, "config_counts": {}}
    batch = [{"R16": ("A", "B"), "QF": ("A",)}]
    merge_config_counts(state, batch)
    merge_config_counts(state, batch)
    key = config_tuple_key("R16", ("A", "B"))
    assert state["config_counts"][key] == 2


def test_reach_merge():
    state = {"total_sims": 0, "reach_counts": {}, "config_counts": {}}
    merge_reach_counts(state, [{"Brazil": "QF", "France": "R16"}], ["R16", "QF", "SF", "final", "winner"])
    assert state["reach_counts"]["Brazil"]["QF"] == 1
    assert state["reach_counts"]["France"]["R16"] == 1
