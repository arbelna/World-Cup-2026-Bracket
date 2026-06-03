from __future__ import annotations

import random
from typing import Protocol

from bracket_simulations.simulator.tiebreak import sample_3way, soft_win_weight


class ProbabilityProvider(Protocol):
    def get(self, team_a: str, team_b: str) -> tuple[float, float, float]: ...


def play_knockout_match(
    team_a: str,
    team_b: str,
    probs: ProbabilityProvider,
    rng: random.Random,
    *,
    alpha_knockout: float,
) -> str:
    pa, pd, pb = probs.get(team_a, team_b)
    outcome = sample_3way(pa, pd, pb, rng)
    if outcome == "a_win":
        return team_a
    if outcome == "b_win":
        return team_b
    et_fn = getattr(probs, "et_win_prob_team_a", None)
    if et_fn is not None:
        w = et_fn(team_a, team_b)
    else:
        w = soft_win_weight(pa, pb, alpha_knockout)
    return team_a if rng.random() < w else team_b
