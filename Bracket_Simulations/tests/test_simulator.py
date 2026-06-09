from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

STAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bracket_simulations.config import load_tournament_config
from bracket_simulations.probabilities.market import MarketProbabilityProvider
from bracket_simulations.probabilities.model import (
    ModelGroupProbabilityProvider,
    ModelKnockoutProbabilityProvider,
)
from bracket_simulations.simulator.bracket_resolver import load_groups, load_knockout_bracket
from bracket_simulations.simulator.group_stage import GroupMatch
from bracket_simulations.simulator.simulator import PARTICIPANT_STAGES, run_single_simulation
from bracket_simulations.tournament_data import build_group_schedule, load_tournament_fixtures


@pytest.fixture(scope="module")
def wc2022_setup():
    cfg = load_tournament_config("wc2022")
    if not cfg.group_pairwise_predictions_file.exists() or not cfg.knockout_pairwise_predictions_file.exists():
        pytest.skip("Run precompute-pairs for wc2022 first")
    groups = load_groups(cfg.groups_file)
    bracket = load_knockout_bracket(cfg.knockout_bracket_file)
    fixtures = load_tournament_fixtures(cfg.fixtures_file, cfg.tournament_id)
    raw_schedule = build_group_schedule(groups, fixtures)
    group_fixtures = {
        label: [GroupMatch(team_a=a, team_b=b) for a, b in matches]
        for label, matches in raw_schedule.items()
    }
    group_model = ModelGroupProbabilityProvider.from_csv(cfg.group_pairwise_predictions_file)
    ko_model = ModelKnockoutProbabilityProvider.from_csv(cfg.knockout_pairwise_predictions_file)
    return cfg, groups, group_fixtures, bracket, group_model, ko_model


def test_single_sim_participant_sizes(wc2022_setup):
    cfg, groups, group_fixtures, bracket, group_model, ko_model = wc2022_setup
    rng = random.Random(42)
    outcome = run_single_simulation(
        groups,
        group_fixtures,
        group_model,
        ko_model,
        bracket,
        rng,
        alphas=cfg.alphas,
    )
    assert len(outcome.participants["R16"]) == 16
    assert len(outcome.participants["QF"]) == 8
    assert len(outcome.participants["SF"]) == 4
    assert len(outcome.participants["final"]) == 2
    assert len(outcome.participants["winner"]) == 1
    for stage in PARTICIPANT_STAGES:
        assert outcome.participants[stage] == tuple(sorted(outcome.participants[stage]))


def test_market_lookup_wc2022():
    cfg = load_tournament_config("wc2022")
    if not cfg.train_dataset.exists():
        pytest.skip("Run sync-inputs first")
    market = MarketProbabilityProvider.from_dataset(
        cfg.train_dataset,
        competition=cfg.match_dataset_filter_competition,
    )
    pa, _, pb = market.get("Argentina", "Australia")
    assert pa > pb


def test_knockout_provider_can_average_stage_context_without_slot():
    provider = ModelKnockoutProbabilityProvider(
        [
            {
                "stage": "R32",
                "slot_id": "1",
                "team_a": "A",
                "team_b": "B",
                "pred_a": 0.60,
                "pred_draw": 0.20,
                "pred_b": 0.20,
            },
            {
                "stage": "R32",
                "slot_id": "2",
                "team_a": "A",
                "team_b": "B",
                "pred_a": 0.50,
                "pred_draw": 0.30,
                "pred_b": 0.20,
            },
        ]
    )
    pa, pd, pb = provider.get("A", "B", stage="R32")
    assert pa == pytest.approx(0.55)
    assert pd == pytest.approx(0.25)
    assert pb == pytest.approx(0.20)
