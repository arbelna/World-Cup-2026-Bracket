from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def soft_win_weight(p_a: float, p_b: float, alpha: float) -> float:
    if p_a <= 0 and p_b <= 0:
        return 0.5
    a = max(p_a, 1e-12) ** alpha
    b = max(p_b, 1e-12) ** alpha
    return a / (a + b)


def pairwise_strength(
    team: str,
    opponents: Sequence[str],
    prob_beats: Callable[[str, str], float],
    alpha: float = 1.0,
) -> float:
    if len(opponents) == 0:
        return 1.0
    total = 0.0
    for opp in opponents:
        p_ij = prob_beats(team, opp)
        p_ji = prob_beats(opp, team)
        denom = p_ij + p_ji
        if denom <= 0:
            total += 0.5
        else:
            total += (p_ij**alpha) / ((p_ij**alpha) + (p_ji**alpha))
    return total / len(opponents)


def weighted_sample_without_replacement(
    items: list[T],
    weights: list[float],
    rng: random.Random,
) -> list[T]:
    remaining = list(items)
    w = [max(float(x), 0.0) for x in weights]
    ordered: list[T] = []
    while remaining:
        total = sum(w)
        if total <= 0:
            pick = rng.randrange(len(remaining))
        else:
            r = rng.random() * total
            acc = 0.0
            pick = 0
            for i, wi in enumerate(w):
                acc += wi
                if r <= acc:
                    pick = i
                    break
        ordered.append(remaining.pop(pick))
        w.pop(pick)
    return ordered


def partition_by_points(teams: Sequence[T], points_fn: Callable[[T], int]) -> dict[int, list[T]]:
    buckets: dict[int, list[T]] = {}
    for team in teams:
        pts = points_fn(team)
        buckets.setdefault(pts, []).append(team)
    return buckets


def rank_by_points_then_tiebreaker(
    teams: Sequence[T],
    points_fn: Callable[[T], int],
    tiebreaker_order: Callable[[list[T]], list[T]],
) -> list[T]:
    buckets = partition_by_points(teams, points_fn)
    ordered: list[T] = []
    for pts in sorted(buckets.keys(), reverse=True):
        cluster = buckets[pts]
        if len(cluster) == 1:
            ordered.extend(cluster)
        else:
            ordered.extend(tiebreaker_order(cluster))
    return ordered


def sample_3way(p_a: float, p_d: float, p_b: float, rng: random.Random) -> str:
    probs = [max(p_a, 0.0), max(p_d, 0.0), max(p_b, 0.0)]
    s = sum(probs)
    if s <= 0:
        return rng.choice(["a_win", "draw", "b_win"])
    probs = [p / s for p in probs]
    r = rng.random()
    if r < probs[0]:
        return "a_win"
    if r < probs[0] + probs[1]:
        return "draw"
    return "b_win"
