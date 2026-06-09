from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

from bracket_simulations.simulator.tiebreak import (
    pairwise_strength,
    rank_by_points_then_tiebreaker,
    sample_3way,
    weighted_sample_without_replacement,
)


class ProbabilityProvider(Protocol):
    def get(
        self,
        team_a: str,
        team_b: str,
        *,
        stage: str | None = None,
        slot_id: str | None = None,
    ) -> tuple[float, float, float]: ...


@dataclass
class GroupMatch:
    team_a: str
    team_b: str


@dataclass
class GroupStanding:
    team: str
    points: int = 0
    played: int = 0


@dataclass
class GroupResult:
    label: str
    teams: list[str]
    standings: list[GroupStanding] = field(default_factory=list)
    rank_order: list[str] = field(default_factory=list)

    def team_at_rank(self, rank: int) -> str:
        return self.rank_order[rank - 1]


@dataclass
class GroupStageResult:
    groups: dict[str, GroupResult]
    third_place: list[tuple[str, str, int]]


def _outcome_points(outcome: str) -> tuple[int, int]:
    if outcome == "a_win":
        return 3, 0
    if outcome == "b_win":
        return 0, 3
    return 1, 1


def _simulate_group_match(
    match: GroupMatch,
    probs: ProbabilityProvider,
    rng: random.Random,
) -> tuple[int, int]:
    pa, pd, pb = probs.get(match.team_a, match.team_b)
    outcome = sample_3way(pa, pd, pb, rng)
    return _outcome_points(outcome)


def _in_group_tiebreaker(
    cluster: list[str],
    group_label: str,
    group_matches: list[GroupMatch],
    probs: ProbabilityProvider,
    rng: random.Random,
    alpha: float,
) -> list[str]:
    def prob_beats(i: str, j: str) -> float:
        for m in group_matches:
            if m.team_a == i and m.team_b == j:
                pa, _, _ = probs.get(i, j)
                return pa
            if m.team_a == j and m.team_b == i:
                _, _, pb = probs.get(j, i)
                return pb
        raise KeyError(f"No group fixture between {i} and {j} in group {group_label}")

    strengths = [
        pairwise_strength(t, [o for o in cluster if o != t], prob_beats, alpha=alpha)
        for t in cluster
    ]
    return weighted_sample_without_replacement(cluster, strengths, rng)


def simulate_group(
    label: str,
    teams: list[str],
    fixtures: list[GroupMatch],
    probs: ProbabilityProvider,
    rng: random.Random,
    *,
    alpha_group_tie: float = 1.0,
) -> GroupResult:
    points = {t: 0 for t in teams}
    for m in fixtures:
        pa_pts, pb_pts = _simulate_group_match(m, probs, rng)
        points[m.team_a] += pa_pts
        points[m.team_b] += pb_pts

    standings = [GroupStanding(team=t, points=points[t], played=3) for t in teams]

    def points_fn(t: str) -> int:
        return points[t]

    def tiebreaker(cluster: list[str]) -> list[str]:
        return _in_group_tiebreaker(cluster, label, fixtures, probs, rng, alpha_group_tie)

    rank_order = rank_by_points_then_tiebreaker(teams, points_fn, tiebreaker)
    return GroupResult(label=label, teams=teams, standings=standings, rank_order=rank_order)


def build_group_fixtures(teams: list[str]) -> list[GroupMatch]:
    matches: list[GroupMatch] = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            matches.append(GroupMatch(team_a=teams[i], team_b=teams[j]))
    return matches


def simulate_all_groups(
    groups: dict[str, list[str]],
    group_probs: ProbabilityProvider,
    rng: random.Random,
    *,
    fixtures_by_group: dict[str, list[GroupMatch]] | None = None,
    alpha_group_tie: float = 1.0,
) -> GroupStageResult:
    results: dict[str, GroupResult] = {}
    third_place: list[tuple[str, str, int]] = []
    for label, teams in groups.items():
        fixtures = fixtures_by_group.get(label, []) if fixtures_by_group is not None else []
        if not fixtures:
            fixtures = build_group_fixtures(teams)
        gr = simulate_group(label, teams, fixtures, group_probs, rng, alpha_group_tie=alpha_group_tie)
        results[label] = gr
        third = gr.team_at_rank(3)
        pts = next(s.points for s in gr.standings if s.team == third)
        third_place.append((third, label, pts))
    return GroupStageResult(groups=results, third_place=third_place)


def r16_participants(gs: GroupStageResult) -> tuple[str, ...]:
    teams: list[str] = []
    for gr in gs.groups.values():
        teams.append(gr.team_at_rank(1))
        teams.append(gr.team_at_rank(2))
    return tuple(sorted(teams))


def rank_third_place_teams(
    third_entries: list[tuple[str, str, int]],
    model_probs: ProbabilityProvider,
    rng: random.Random,
    *,
    alpha: float = 1.0,
    take: int = 8,
    stage_context: str = "R32",
) -> list[tuple[str, str]]:
    def points_fn(entry: tuple[str, str, int]) -> int:
        return entry[2]

    def tiebreaker(cluster: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
        teams = [e[0] for e in cluster]

        def prob_beats(i: str, j: str) -> float:
            pa, _, _ = model_probs.get(i, j, stage=stage_context)
            return pa

        strengths = [
            pairwise_strength(t, [o for o in teams if o != t], prob_beats, alpha=alpha)
            for t in teams
        ]
        ordered_teams = weighted_sample_without_replacement(teams, strengths, rng)
        team_to_entry = {e[0]: e for e in cluster}
        return [team_to_entry[t] for t in ordered_teams]

    ordered = rank_by_points_then_tiebreaker(third_entries, points_fn, tiebreaker)
    return [(e[0], e[1]) for e in ordered[:take]]


def r32_participants(gs: GroupStageResult, third_ranked: list[tuple[str, str]]) -> tuple[str, ...]:
    teams: list[str] = []
    for gr in gs.groups.values():
        teams.append(gr.team_at_rank(1))
        teams.append(gr.team_at_rank(2))
    for team, _grp in third_ranked:
        teams.append(team)
    return tuple(sorted(teams))
