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
from bracket_simulations.simulator.bracket_resolver import load_groups, load_knockout_bracket
from bracket_simulations.simulator.simulator import PARTICIPANT_STAGES, run_single_simulation


@pytest.fixture(scope="module")
def wc2022_setup():
    cfg = load_tournament_config("wc2022")
    if not cfg.pairwise_predictions_file.exists():
        pytest.skip("Run precompute-pairs for wc2022 first")
    groups = load_groups(cfg.groups_file)
    bracket = load_knockout_bracket(cfg.knockout_bracket_file)
    from bracket_simulations.probabilities.model import ModelProbabilityProvider

    model = ModelProbabilityProvider.from_csv(cfg.pairwise_predictions_file)
    return cfg, groups, bracket, model


def test_single_sim_participant_sizes(wc2022_setup):
    cfg, groups, bracket, model = wc2022_setup
    rng = random.Random(42)
    outcome = run_single_simulation(groups, model, model, bracket, rng, alphas=cfg.alphas)
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
