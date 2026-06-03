from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bracket_simulations.config import load_tournament_config
from bracket_simulations.parsers.old_stats_parser import parse_old_stats_file
from bracket_simulations.paths import FIXTURES_STATS, MATCH_DATASET, OLD_STATS_DIR
from bracket_simulations.simulator.bracket_resolver import load_groups, load_knockout_bracket, resolve_team_ref
from bracket_simulations.utils.matching import normalize_team_name, normalized_team_pair

WC_FINALS_PATHS: dict[str, Path] = {
    "wc2010": OLD_STATS_DIR / "2010--south-africa" / "cup_finals.txt",
    "wc2014": OLD_STATS_DIR / "2014--brazil" / "cup_finals.txt",
    "wc2018": OLD_STATS_DIR / "2018--russia" / "cup_finals.txt",
    "wc2022": OLD_STATS_DIR / "2022--qatar" / "cup_finals.txt",
}


def _dataset_team_index(competition: str) -> dict[str, str]:
    rows = json.loads(MATCH_DATASET.read_text(encoding="utf-8"))
    index: dict[str, str] = {}
    for row in rows:
        if row.get("competition") != competition:
            continue
        for key in ("team_a", "team_b"):
            name = str(row[key])
            index[normalize_team_name(name)] = name
    return index


def _resolve_team_name(raw: str, index: dict[str, str]) -> str:
    key = normalize_team_name(raw)
    if key in index:
        return index[key]
    compact = key.replace(" ", "")
    for norm, display in index.items():
        if norm.replace(" ", "") == compact:
            return display
    return raw.strip()


STAGES = ["R16", "QF", "SF", "final", "winner"]
EXPECTED_N = {"R16": 16, "QF": 8, "SF": 4, "final": 2, "winner": 1}
STAGE_ORDER = ["group", "R16", "QF", "SF", "final", "winner"]

OFFICIAL_GROUP_ORDER: dict[str, dict[str, list[str]]] = {
    "wc2022": {
        "A": ["Netherlands", "Senegal", "Ecuador", "Qatar"],
        "B": ["England", "United States", "Iran", "Wales"],
        "C": ["Argentina", "Poland", "Mexico", "Saudi Arabia"],
        "D": ["France", "Australia", "Tunisia", "Denmark"],
        "E": ["Japan", "Spain", "Germany", "Costa Rica"],
        "F": ["Morocco", "Croatia", "Belgium", "Canada"],
        "G": ["Brazil", "Switzerland", "Cameroon", "Serbia"],
        "H": ["Portugal", "South Korea", "Uruguay", "Ghana"],
    },
}


@dataclass
class ActualOutcome:
    actual_at_least: dict[str, set[str]]
    actual_config: dict[str, tuple[str, ...]]
    reach: dict[str, str]
    champion: str


class _GroupResult:
    def __init__(self, rank_order: list[str]) -> None:
        self.rank_order = rank_order

    def team_at_rank(self, rank: int) -> str:
        return self.rank_order[rank - 1]


def _load_match_index(competition: str) -> dict[frozenset[str], dict]:
    rows = json.loads(MATCH_DATASET.read_text(encoding="utf-8"))
    index: dict[frozenset[str], dict] = {}
    for row in rows:
        if row.get("competition") != competition:
            continue
        key = frozenset({normalize_team_name(row["team_a"]), normalize_team_name(row["team_b"])})
        index[key] = row
    return index


def _load_fixture_winners(tournament: str, competition: str) -> dict[frozenset[str], str]:
    """Knockout winners from cup_finals.txt (handles pens/ET); group from fixtures scores."""
    index = _dataset_team_index(competition)
    winners: dict[frozenset[str], str] = {}

    finals_path = WC_FINALS_PATHS[tournament]
    for match in parse_old_stats_file(finals_path):
        if match.stage == "group" or match.advancing_team is None:
            continue
        t1 = _resolve_team_name(match.team1, index)
        t2 = _resolve_team_name(match.team2, index)
        adv = _resolve_team_name(match.advancing_team, index)
        winners[normalized_team_pair(t1, t2)] = adv

    tournament_id = load_tournament_config(tournament).tournament_id
    fixtures = json.loads(FIXTURES_STATS.read_text(encoding="utf-8"))
    match_index = _load_match_index(competition)
    for fx in fixtures:
        if fx.get("tournament_id") != tournament_id:
            continue
        home = fx["home_team"]
        away = fx["away_team"]
        key = normalized_team_pair(home, away)
        if key in winners:
            continue
        meta = match_index.get(key)
        if meta is None or meta.get("stage") == "group":
            continue
        hs = fx.get("home_score")
        aw = fx.get("away_score")
        if hs is None or aw is None or hs == aw:
            continue
        winner = home if hs > aw else away
        winners[key] = winner
    return winners


def _group_results_from_points(tournament: str, competition: str, groups: dict[str, list[str]]) -> dict[str, _GroupResult]:
    match_index = _load_match_index(competition)
    fixtures = json.loads(FIXTURES_STATS.read_text(encoding="utf-8"))
    tournament_id = load_tournament_config(tournament).tournament_id
    out: dict[str, _GroupResult] = {}

    for gl, teams in groups.items():
        if tournament in OFFICIAL_GROUP_ORDER:
            out[gl] = _GroupResult(OFFICIAL_GROUP_ORDER[tournament][gl])
            continue
        pts: dict[str, int] = defaultdict(int)
        gd: dict[str, int] = defaultdict(int)
        gf: dict[str, int] = defaultdict(int)
        team_set = set(teams)
        for fx in fixtures:
            if fx.get("tournament_id") != tournament_id:
                continue
            home = fx["home_team"]
            away = fx["away_team"]
            if home not in team_set or away not in team_set:
                continue
            key = normalized_team_pair(home, away)
            meta = match_index.get(key)
            if meta is None or meta.get("stage") != "group":
                continue
            hs = fx.get("home_score")
            aw = fx.get("away_score")
            if hs is None or aw is None:
                continue
            gf[home] += hs
            gf[away] += aw
            gd[home] += hs - aw
            gd[away] += aw - hs
            if hs > aw:
                pts[home] += 3
            elif aw > hs:
                pts[away] += 3
            else:
                pts[home] += 1
                pts[away] += 1
        order = sorted(teams, key=lambda t: (-pts[t], -gd[t], -gf[t], t))
        out[gl] = _GroupResult(order)
    return out


def build_actual_outcome(tournament: str) -> ActualOutcome:
    cfg = load_tournament_config(tournament)
    groups = load_groups(cfg.groups_file)
    bracket = load_knockout_bracket(cfg.knockout_bracket_file)
    fixture_winners = _load_fixture_winners(tournament, cfg.match_dataset_filter_competition)
    gr_objs = _group_results_from_points(tournament, cfg.match_dataset_filter_competition, groups)

    def winner_of(ha: str, hb: str) -> str:
        key = normalized_team_pair(ha, hb)
        if key not in fixture_winners:
            raise ValueError(f"No result for knockout match {ha} vs {hb}")
        return fixture_winners[key]

    reach: dict[str, str] = {t: "group" for ts in groups.values() for t in ts}
    participants: dict[str, tuple[str, ...]] = {}

    def record(team: str, stage: str) -> None:
        if STAGE_ORDER.index(stage) > STAGE_ORDER.index(reach[team]):
            reach[team] = stage

    r16_teams: list[str] = []
    for gr in gr_objs.values():
        record(gr.team_at_rank(1), "R16")
        record(gr.team_at_rank(2), "R16")
        r16_teams.extend([gr.team_at_rank(1), gr.team_at_rank(2)])
    participants["R16"] = tuple(sorted(r16_teams))

    r16_pairs = [
        (resolve_team_ref(m["home"], gr_objs), resolve_team_ref(m["away"], gr_objs))
        for m in bracket["r16"]
    ]
    next_stage = {"R16": "QF", "QF": "SF", "SF": "final", "final": "winner"}

    def play_round(pairs: list[tuple[str, str]], stage: str) -> list[str]:
        winners: list[str] = []
        for a, b in pairs:
            w = winner_of(a, b)
            record(w, next_stage[stage])
            winners.append(w)
        return winners

    r16_w = play_round(r16_pairs, "R16")
    participants["QF"] = tuple(sorted(r16_w))
    qf_pairs = [(r16_w[m["home_idx"]], r16_w[m["away_idx"]]) for m in bracket["qf"]]
    qf_w = play_round(qf_pairs, "QF")
    participants["SF"] = tuple(sorted(qf_w))
    sf_pairs = [(qf_w[m["home_idx"]], qf_w[m["away_idx"]]) for m in bracket["sf"]]
    sf_w = play_round(sf_pairs, "SF")
    participants["final"] = tuple(sorted(sf_w))
    fi = bracket["final"]
    final_pair = (sf_w[fi["home_idx"]], sf_w[fi["away_idx"]])
    final_w = winner_of(*final_pair)
    reach[final_w] = "winner"
    loser = final_pair[1] if final_pair[0] == final_w else final_pair[0]
    reach[loser] = "final"
    participants["winner"] = (final_w,)

    actual_at_least = {s: set() for s in STAGES}
    for team, exit_stage in reach.items():
        if exit_stage == "group":
            continue
        idx = STAGE_ORDER.index(exit_stage)
        for s in STAGES:
            if STAGE_ORDER.index(s) <= idx:
                actual_at_least[s].add(team)

    champion = final_w
    return ActualOutcome(
        actual_at_least=actual_at_least,
        actual_config=participants,
        reach=reach,
        champion=champion,
    )
