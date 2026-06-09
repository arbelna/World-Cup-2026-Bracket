#!/usr/bin/env python3
"""Build wc*_groups.json and knockout brackets from old_stats cup.txt."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = STAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bracket_simulations.paths import DATA_INPUT, MATCH_DATASET, OLD_STATS_DIR
from bracket_simulations.utils.matching import normalize_team_name

WC_CUP_PATHS: dict[str, Path] = {
    "wc2010": OLD_STATS_DIR / "2010--south-africa" / "cup.txt",
    "wc2014": OLD_STATS_DIR / "2014--brazil" / "cup.txt",
    "wc2018": OLD_STATS_DIR / "2018--russia" / "cup.txt",
    "wc2022": OLD_STATS_DIR / "2022--qatar" / "cup.txt",
}
WC_COMPETITIONS: dict[str, str] = {
    "wc2010": "World Cup 2010",
    "wc2014": "World Cup 2014",
    "wc2018": "World Cup 2018",
    "wc2022": "World Cup 2022",
}
WC2026_SQUADS_PATH = DATA_INPUT / "wc2026_tournament_squads_with_value.json"
KNOCKOUT_TEMPLATE = DATA_INPUT / "knockout_bracket_template.json"
KNOCKOUT_COPY_TO = ("wc2010", "wc2014", "wc2018", "wc2022")
HISTORICAL_HOST_COUNTRIES: dict[str, str] = {
    "wc2010": "South Africa",
    "wc2014": "Brazil",
    "wc2018": "Russia",
    "wc2022": "Qatar",
}
WC2026_KNOCKOUT_CONTEXT: dict[str, dict[str, str]] = {
    "R32": {
        "73": "Mexico",
        "74": "United States",
        "75": "United States",
        "76": "Canada",
        "77": "United States",
        "78": "Mexico",
        "79": "United States",
        "80": "Canada",
        "81": "United States",
        "82": "Mexico",
        "83": "Canada",
        "84": "United States",
        "85": "Mexico",
        "86": "United States",
        "87": "Canada",
        "88": "United States",
    },
    "R16": {
        "1": "Mexico",
        "2": "United States",
        "3": "Canada",
        "4": "United States",
        "5": "Mexico",
        "6": "United States",
        "7": "Canada",
        "8": "United States",
    },
    "QF": {
        "1": "United States",
        "2": "Mexico",
        "3": "United States",
        "4": "Canada",
    },
    "SF": {
        "1": "United States",
        "2": "Mexico",
    },
    "final": {"1": "United States"},
    "third_place": {"1": "Canada"},
}


def _build_wc2026_groups() -> dict[str, list[str]]:
    payload = json.loads(WC2026_SQUADS_PATH.read_text(encoding="utf-8"))
    tournaments = payload.get("tournaments", [])
    if not tournaments:
        raise ValueError("Missing tournaments in wc2026_tournament_squads_with_value.json")
    teams = tournaments[0].get("teams", [])
    groups: dict[str, list[str]] = {}
    combined_dataset = DATA_INPUT / "match_dataset_with_wc2026.json"
    dataset_for_index = combined_dataset if combined_dataset.exists() else MATCH_DATASET
    wc2026_index = _dataset_team_index("World Cup 2026", dataset_for_index)
    for team in teams:
        label = str(team.get("group", "")).strip().upper()
        if label.startswith("GROUP "):
            label = label.replace("GROUP ", "", 1).strip()
        if not label:
            continue
        groups.setdefault(label, []).append(_resolve_team(str(team.get("team_name")), wc2026_index))
    expected = [chr(ord("A") + i) for i in range(12)]
    if sorted(groups.keys()) != expected:
        raise ValueError(f"WC2026 groups must be A-L; got {sorted(groups.keys())}")
    for label, members in groups.items():
        if len(members) != 4:
            raise ValueError(f"Group {label} must have 4 teams, got {len(members)}")
    return groups


def _write_wc2026_knockout_bracket() -> None:
    bracket = {
        "r32": [
            {"id": 73, "home": "2A", "away": "2B"},
            {"id": 74, "home": "1E", "away": {"type": "third_slot", "slot": "1A"}},
            {"id": 75, "home": "1F", "away": "2C"},
            {"id": 76, "home": "1C", "away": "2F"},
            {"id": 77, "home": "1I", "away": {"type": "third_slot", "slot": "1B"}},
            {"id": 78, "home": "2E", "away": "2I"},
            {"id": 79, "home": "1A", "away": {"type": "third_slot", "slot": "1K"}},
            {"id": 80, "home": "1L", "away": {"type": "third_slot", "slot": "1L"}},
            {"id": 81, "home": "1D", "away": {"type": "third_slot", "slot": "1D"}},
            {"id": 82, "home": "1G", "away": {"type": "third_slot", "slot": "1G"}},
            {"id": 83, "home": "2K", "away": "2L"},
            {"id": 84, "home": "1H", "away": "2J"},
            {"id": 85, "home": "1B", "away": {"type": "third_slot", "slot": "1E"}},
            {"id": 86, "home": "1J", "away": "2H"},
            {"id": 87, "home": "1K", "away": {"type": "third_slot", "slot": "1I"}},
            {"id": 88, "home": "2D", "away": "2G"},
        ],
        "r16": [
            {"home_match": 74, "away_match": 77},
            {"home_match": 73, "away_match": 75},
            {"home_match": 76, "away_match": 78},
            {"home_match": 79, "away_match": 80},
            {"home_match": 83, "away_match": 84},
            {"home_match": 81, "away_match": 82},
            {"home_match": 86, "away_match": 88},
            {"home_match": 85, "away_match": 87},
        ],
        "qf": [{"home_idx": i, "away_idx": i + 1} for i in range(0, 8, 2)],
        "sf": [{"home_idx": 0, "away_idx": 1}, {"home_idx": 2, "away_idx": 3}],
        "final": {"home_idx": 0, "away_idx": 1},
        "third_place": {"home_idx": 0, "away_idx": 1, "losers_from": "sf"},
    }
    out = DATA_INPUT / "wc2026_knockout_bracket.json"
    out.write_text(json.dumps(bracket, indent=2), encoding="utf-8")
    print(f"Wrote {out.name}")


def _dataset_team_index(competition: str, dataset_path: Path = MATCH_DATASET) -> dict[str, str]:
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    index: dict[str, str] = {}
    for row in rows:
        if row.get("competition") != competition:
            continue
        for key in ("team_a", "team_b"):
            name = str(row[key])
            index[normalize_team_name(name)] = name
    return index


def _resolve_team(raw: str, index: dict[str, str]) -> str:
    key = normalize_team_name(raw)
    if key in index:
        return index[key]
    compact = key.replace(" ", "")
    for norm, display in index.items():
        if norm.replace(" ", "") == compact:
            return display
    return raw.strip()


def _build_combined_match_dataset() -> None:
    base_rows = json.loads(MATCH_DATASET.read_text(encoding="utf-8"))
    wc2026_path = DATA_INPUT / "wc2026_match_dataset.json"
    if not wc2026_path.exists():
        out = DATA_INPUT / "match_dataset_with_wc2026.json"
        out.write_text(json.dumps(base_rows, indent=2), encoding="utf-8")
        print(f"Wrote {out.name} (legacy12 only; wc2026 dataset not found)")
        return
    wc2026_rows = json.loads(wc2026_path.read_text(encoding="utf-8"))
    out = DATA_INPUT / "match_dataset_with_wc2026.json"
    out.write_text(json.dumps(base_rows + wc2026_rows, indent=2), encoding="utf-8")
    print(f"Wrote {out.name} ({len(base_rows)} legacy + {len(wc2026_rows)} wc2026 rows)")


def parse_groups_from_cup(cup_path: Path) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for line in cup_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^Group\s+([A-H])\s+\|\s+(.+)$", line.strip())
        if not m:
            continue
        label = m.group(1)
        parts = [p.strip() for p in re.split(r"\s{2,}", m.group(2).strip()) if p.strip()]
        if len(parts) != 4:
            parts = [t for t in m.group(2).split() if t.strip()]
        if len(parts) != 4:
            raise ValueError(f"Group {label} in {cup_path}: expected 4 teams, got {parts!r}")
        groups[label] = parts
    if len(groups) != 8:
        raise ValueError(f"{cup_path}: expected 8 groups, got {len(groups)}")
    return groups


def build_wc_groups(slug: str) -> dict:
    cup = WC_CUP_PATHS[slug]
    competition = WC_COMPETITIONS[slug]
    index = _dataset_team_index(competition)
    raw = parse_groups_from_cup(cup)
    resolved = {label: [_resolve_team(t, index) for t in teams] for label, teams in raw.items()}
    return {"groups": resolved}


def copy_knockout_brackets() -> None:
    if not KNOCKOUT_TEMPLATE.exists():
        raise FileNotFoundError(KNOCKOUT_TEMPLATE)
    for slug in KNOCKOUT_COPY_TO:
        dest = DATA_INPUT / f"{slug}_knockout_bracket.json"
        shutil.copy2(KNOCKOUT_TEMPLATE, dest)
        print(f"Wrote {dest.name}")


def _historical_knockout_context(slug: str) -> dict[str, dict[str, str]]:
    host_country = HISTORICAL_HOST_COUNTRIES[slug]
    return {
        "R16": {str(idx + 1): host_country for idx in range(8)},
        "QF": {str(idx + 1): host_country for idx in range(4)},
        "SF": {str(idx + 1): host_country for idx in range(2)},
        "final": {"1": host_country},
        "third_place": {"1": host_country},
    }


def write_knockout_contexts() -> None:
    for slug in KNOCKOUT_COPY_TO:
        out = DATA_INPUT / f"{slug}_knockout_context.json"
        out.write_text(json.dumps(_historical_knockout_context(slug), indent=2), encoding="utf-8")
        print(f"Wrote {out.name}")
    wc2026_out = DATA_INPUT / "wc2026_knockout_context.json"
    wc2026_out.write_text(json.dumps(WC2026_KNOCKOUT_CONTEXT, indent=2), encoding="utf-8")
    print(f"Wrote {wc2026_out.name}")


def main() -> None:
    DATA_INPUT.mkdir(parents=True, exist_ok=True)
    _build_combined_match_dataset()
    for slug in WC_CUP_PATHS:
        data = build_wc_groups(slug)
        out = DATA_INPUT / f"{slug}_groups.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        n_teams = sum(len(t) for t in data["groups"].values())
        print(f"{slug}: {len(data['groups'])} groups, {n_teams} teams -> {out.name}")
    wc2026_groups = {"groups": _build_wc2026_groups()}
    wc2026_out = DATA_INPUT / "wc2026_groups.json"
    wc2026_out.write_text(json.dumps(wc2026_groups, indent=2), encoding="utf-8")
    n_teams = sum(len(t) for t in wc2026_groups["groups"].values())
    print(f"wc2026: {len(wc2026_groups['groups'])} groups, {n_teams} teams -> {wc2026_out.name}")
    copy_knockout_brackets()
    _write_wc2026_knockout_bracket()
    write_knockout_contexts()


if __name__ == "__main__":
    main()
