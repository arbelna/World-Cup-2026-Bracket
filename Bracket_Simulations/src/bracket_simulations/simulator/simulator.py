from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from bracket_simulations.simulator.bracket_resolver import resolve_r32_pairing, resolve_team_ref
from bracket_simulations.simulator.group_stage import (
    r32_participants,
    r16_participants,
    rank_third_place_teams,
    simulate_all_groups,
)
from bracket_simulations.simulator.knockout import play_knockout_match

STAGE_ORDER = ["group", "R32", "R16", "QF", "SF", "final", "winner"]
PARTICIPANT_STAGES = ("R16", "QF", "SF", "final", "winner")


@dataclass
class SimulationReach:
    stages: dict[str, str] = field(default_factory=dict)


@dataclass
class SimulationOutcome:
    stages: dict[str, str]
    participants: dict[str, tuple[str, ...]]
    combination_id: int | None = None
    third_place_qualifiers: tuple[str, ...] | None = None


def _record_stage(reach: SimulationReach, team: str, stage: str) -> None:
    current = reach.stages.get(team, "group")
    if STAGE_ORDER.index(stage) > STAGE_ORDER.index(current):
        reach.stages[team] = stage


def _sorted_winners(winners: list[str]) -> tuple[str, ...]:
    return tuple(sorted(winners))


def _play_round(
    matches: list[tuple[str, str]],
    stage: str,
    ko_probs: Any,
    rng: random.Random,
    alpha: float,
    reach: SimulationReach,
) -> tuple[list[str], list[str]]:
    winners: list[str] = []
    losers: list[str] = []
    next_stage = {"R32": "R16", "R16": "QF", "QF": "SF", "SF": "final", "final": "winner"}.get(stage, stage)
    for a, b in matches:
        w = play_knockout_match(a, b, ko_probs, rng, alpha_knockout=alpha)
        l = b if w == a else a
        winners.append(w)
        losers.append(l)
        _record_stage(reach, w, next_stage)
    return winners, losers


def _run_knockout_tree(
    bracket: dict[str, Any],
    first_round: list[tuple[str, str, str]],
    ko_probs: Any,
    rng: random.Random,
    alphas: dict[str, float],
    reach: SimulationReach,
    participants: dict[str, tuple[str, ...]],
) -> SimulationOutcome:
    stage_name = first_round[0][0] if first_round else "R16"
    alpha = alphas.get(stage_name, 0.5)
    pairs = [(a, b) for _s, a, b in first_round]
    first_winners, _ = _play_round(pairs, stage_name, ko_probs, rng, alpha, reach)
    if stage_name == "R32":
        participants["R16"] = _sorted_winners(first_winners)
        r16_pairs = [(first_winners[m["home_idx"]], first_winners[m["away_idx"]]) for m in bracket["r16"]]
        r16_winners, _ = _play_round(r16_pairs, "R16", ko_probs, rng, alphas.get("R16", 0.5), reach)
    else:
        r16_winners = first_winners
    participants["QF"] = _sorted_winners(r16_winners)

    qf_pairs = [(r16_winners[m["home_idx"]], r16_winners[m["away_idx"]]) for m in bracket["qf"]]
    qf_winners, _ = _play_round(qf_pairs, "QF", ko_probs, rng, alphas.get("QF", 0.5), reach)
    participants["SF"] = _sorted_winners(qf_winners)

    sf_pairs = [(qf_winners[m["home_idx"]], qf_winners[m["away_idx"]]) for m in bracket["sf"]]
    sf_winners, sf_losers = _play_round(sf_pairs, "SF", ko_probs, rng, alphas.get("SF", 0.5), reach)
    participants["final"] = _sorted_winners(sf_winners)

    fi = bracket["final"]
    final_pair = (sf_winners[fi["home_idx"]], sf_winners[fi["away_idx"]])
    final_winners, final_losers = _play_round(
        [final_pair], "final", ko_probs, rng, alphas.get("final", 0.5), reach
    )
    participants["winner"] = _sorted_winners(final_winners)
    _record_stage(reach, final_losers[0], "final")

    if len(sf_losers) >= 2:
        tp = bracket.get("third_place", {})
        if tp.get("losers_from") == "sf":
            bronze_pair = (sf_losers[tp["home_idx"]], sf_losers[tp["away_idx"]])
        else:
            bronze_pair = (sf_losers[0], sf_losers[1])
        play_knockout_match(
            bronze_pair[0],
            bronze_pair[1],
            ko_probs,
            rng,
            alpha_knockout=alphas.get("third_place", 0.5),
        )

    return SimulationOutcome(stages=dict(reach.stages), participants=participants)


def simulate_wc32(
    groups: dict[str, list[str]],
    group_probs: Any,
    ko_probs: Any,
    bracket: dict[str, Any],
    rng: random.Random,
    *,
    alphas: dict[str, float],
) -> SimulationOutcome:
    reach = SimulationReach()
    participants: dict[str, tuple[str, ...]] = {}
    for t in (team for ts in groups.values() for team in ts):
        reach.stages[t] = "group"

    gs = simulate_all_groups(groups, group_probs, rng, alpha_group_tie=alphas.get("group_tie", 1.0))
    participants["R16"] = r16_participants(gs)

    for _label, gr in gs.groups.items():
        _record_stage(reach, gr.team_at_rank(1), "R16")
        _record_stage(reach, gr.team_at_rank(2), "R16")

    r16_matches: list[tuple[str, str, str]] = []
    for m in bracket["r16"]:
        a = resolve_team_ref(str(m["home"]), gs.groups)
        b = resolve_team_ref(str(m["away"]), gs.groups)
        r16_matches.append(("R16", a, b))

    return _run_knockout_tree(bracket, r16_matches, ko_probs, rng, alphas, reach, participants)


def simulate_wc48(
    groups: dict[str, list[str]],
    group_probs: Any,
    ko_probs: Any,
    bracket: dict[str, Any],
    scenarios_index: dict[tuple[str, ...], dict[str, Any]],
    rng: random.Random,
    *,
    best_third_qualifiers: int,
    stop_after_group: bool,
    alphas: dict[str, float],
) -> SimulationOutcome:
    reach = SimulationReach()
    participants: dict[str, tuple[str, ...]] = {}
    for t in (team for ts in groups.values() for team in ts):
        reach.stages[t] = "group"

    gs = simulate_all_groups(groups, group_probs, rng, alpha_group_tie=alphas.get("group_tie", 1.0))

    for _label, gr in gs.groups.items():
        first = gr.team_at_rank(1)
        second = gr.team_at_rank(2)
        _record_stage(reach, first, "R32")
        _record_stage(reach, second, "R32")

    third_ranked = rank_third_place_teams(
        gs.third_place,
        ko_probs,
        rng,
        alpha=alphas.get("group_tie", 1.0),
        take=best_third_qualifiers,
    )
    qualifying_groups = tuple(sorted(g for _, g in third_ranked))
    scenario = scenarios_index[qualifying_groups]
    combination_id = int(scenario["option"])
    participants["R32"] = r32_participants(gs, third_ranked)

    for team, _grp in third_ranked:
        _record_stage(reach, team, "R32")

    if stop_after_group:
        return SimulationOutcome(
            stages=dict(reach.stages),
            participants=participants,
            combination_id=combination_id,
            third_place_qualifiers=qualifying_groups,
        )

    r32_winners: dict[int, str] = {}
    for m in bracket["r32"]:
        mid = int(m["id"])
        a, b = resolve_r32_pairing(m, gs.groups, scenario)
        w = play_knockout_match(a, b, ko_probs, rng, alpha_knockout=alphas.get("R32", 0.5))
        r32_winners[mid] = w
        _record_stage(reach, w, "R16")
    participants["R16"] = _sorted_winners(list(r32_winners.values()))
    r16_matches = [("R16", r32_winners[int(m["home_match"])], r32_winners[int(m["away_match"])]) for m in bracket["r16"]]
    outcome = _run_knockout_tree(bracket, r16_matches, ko_probs, rng, alphas, reach, participants)
    return SimulationOutcome(
        stages=outcome.stages,
        participants=outcome.participants,
        combination_id=combination_id,
        third_place_qualifiers=qualifying_groups,
    )


def run_single_simulation(
    groups: dict[str, list[str]],
    group_probs: Any,
    ko_probs: Any,
    bracket: dict[str, Any],
    rng: random.Random,
    *,
    scenarios_index: dict[tuple[str, ...], dict[str, Any]] | None = None,
    best_third_qualifiers: int = 0,
    stop_after_group: bool = False,
    alphas: dict[str, float],
) -> SimulationOutcome:
    if best_third_qualifiers > 0:
        if scenarios_index is None:
            raise ValueError("R32 scenarios required for WC2026")
        return simulate_wc48(
            groups,
            group_probs,
            ko_probs,
            bracket,
            scenarios_index,
            rng,
            best_third_qualifiers=best_third_qualifiers,
            stop_after_group=stop_after_group,
            alphas=alphas,
        )
    return simulate_wc32(groups, group_probs, ko_probs, bracket, rng, alphas=alphas)
