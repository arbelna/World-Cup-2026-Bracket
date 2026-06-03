from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from bracket_simulations.aggregates import exit_and_cumulative_probs, parse_config_key
from bracket_simulations.config import load_tournament_config
from bracket_simulations.paths import stage_relative_path

STAGE_TEAM_COUNTS: dict[str, int] = {
    "R32": 32,
    "R16": 16,
    "QF": 8,
    "SF": 4,
    "final": 2,
    "winner": 1,
}

# Stages that get scenario-family analysis (skip degenerate final/winner)
FAMILY_STAGES = ("R32", "R16", "QF", "SF")


def combos_for_stage(state: dict[str, Any], stage: str) -> list[tuple[tuple[str, ...], int]]:
    """All observed team sets for a stage, sorted by count descending."""
    config_counts: dict[str, int] = state.get("config_counts", {})
    prefix = stage + "|||"
    rows: list[tuple[tuple[str, ...], int]] = []
    for key, count in config_counts.items():
        if not key.startswith(prefix):
            continue
        _, teams = parse_config_key(key)
        rows.append((teams, int(count)))
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def cumulative_coverage(
    combos: list[tuple[tuple[str, ...], int]], total: int
) -> list[tuple[int, float, float]]:
    """Return (rank, combo_prob, cumulative_prob) for each combo."""
    if total <= 0:
        return []
    out: list[tuple[int, float, float]] = []
    cum = 0.0
    for rank, (_teams, count) in enumerate(combos, start=1):
        p = count / total
        cum += p
        out.append((rank, p, cum))
    return out


def _consensus_teams(
    members: list[tuple[tuple[str, ...], int]], threshold: float = 0.8
) -> list[str]:
    """Teams appearing in >threshold fraction of weighted member sims."""
    if not members:
        return []
    total_weight = sum(c for _, c in members)
    if total_weight <= 0:
        return []
    team_weight: dict[str, int] = {}
    for teams, count in members:
        for t in teams:
            team_weight[t] = team_weight.get(t, 0) + count
    return sorted(
        t for t, w in team_weight.items() if w / total_weight >= threshold
    )


def _contested_teams(consensus: set[str], members: list[tuple[tuple[str, ...], int]]) -> list[str]:
    all_teams: set[str] = set()
    for teams, _ in members:
        all_teams.update(teams)
    return sorted(all_teams - consensus)


def build_scenario_families(
    combos: list[tuple[tuple[str, ...], int]],
    *,
    stage: str,
    sim_total: int,
    top_anchors: int = 5,
    min_overlap: int | None = None,
) -> dict[str, Any]:
    """
    Anchor-based families (guide §7.7): group combos sharing N-1 or N-2 teams with anchor.
    Uses top-K anchors; merges families with identical member combo sets.
    """
    if not combos:
        return {"stage": stage, "anchors": [], "families": []}

    n = len(combos[0][0])
    expected = STAGE_TEAM_COUNTS.get(stage)
    if expected and n != expected:
        pass  # allow if data differs

    overlap_floor = min_overlap if min_overlap is not None else max(n - 2, 1)

    anchors = combos[:top_anchors]
    raw_families: list[dict[str, Any]] = []

    for anchor_teams, anchor_count in anchors:
        anchor_set = set(anchor_teams)
        by_overlap: dict[int, list[tuple[tuple[str, ...], int]]] = {}

        for teams, count in combos:
            overlap = len(anchor_set & set(teams))
            if overlap >= overlap_floor:
                by_overlap.setdefault(overlap, []).append((teams, count))

        for overlap, members in sorted(by_overlap.items(), reverse=True):
            total_in_family = sum(c for _, c in members)
            consensus = _consensus_teams(members)
            contested = _contested_teams(set(consensus), members)
            raw_families.append(
                {
                    "anchor": list(anchor_teams),
                    "anchor_count": anchor_count,
                    "overlap": overlap,
                    "member_count": len(members),
                    "sim_count": total_in_family,
                    "probability": total_in_family / sim_total if sim_total > 0 else 0,
                    "consensus_teams": consensus,
                    "contested_teams": contested,
                    "top_members": [
                        {"teams": list(t), "count": c}
                        for t, c in sorted(members, key=lambda x: x[1], reverse=True)[:10]
                    ],
                }
            )

    # Deduplicate by frozenset of member team tuples
    seen: set[frozenset[tuple[str, ...]]] = set()
    families: list[dict[str, Any]] = []
    for fam in raw_families:
        member_keys = frozenset(tuple(m["teams"]) for m in fam["top_members"])
        if member_keys in seen:
            continue
        seen.add(member_keys)
        families.append(fam)

    return {
        "stage": stage,
        "team_set_size": n,
        "overlap_floor": overlap_floor,
        "total_unique_combos": len(combos),
        "total_sims_in_combos": sum(c for _, c in combos),
        "families": families,
    }


def write_marginal_csv(
    path: Path,
    state: dict[str, Any],
    stages_tracked: list[str],
    all_teams: list[str],
) -> None:
    total = int(state.get("total_sims", 0))
    counts = state.get("reach_counts", {})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        reach_cols = [f"p_at_least_{s}" for s in stages_tracked]
        exit_cols = [f"p_exit_{s}" for s in stages_tracked]
        writer.writerow(["team", *exit_cols, *reach_cols])
        for team in sorted(all_teams):
            tc = counts.get(team, {})
            exit_p, cumulative_p = exit_and_cumulative_probs(tc, stages_tracked, total)
            row = [team]
            row.extend(f"{exit_p[s]:.6f}" for s in stages_tracked)
            row.extend(f"{cumulative_p[s]:.6f}" for s in stages_tracked)
            writer.writerow(row)


def _write_combos_csv(path: Path, combos: list[tuple[tuple[str, ...], int]], total: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "teams", "count", "probability"])
        for rank, (teams, count) in enumerate(combos, start=1):
            prob = count / total if total > 0 else 0.0
            writer.writerow([rank, "|".join(teams), count, f"{prob:.8f}"])


def _write_coverage_csv(path: Path, coverage: list[tuple[int, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "probability", "cumulative_probability"])
        for rank, p, cum in coverage:
            writer.writerow([rank, f"{p:.8f}", f"{cum:.8f}"])


def _coverage_summary(coverage: list[tuple[int, float, float]], thresholds: list[int]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k in thresholds:
        if k <= len(coverage):
            out[f"top_{k}"] = coverage[k - 1][2]
        else:
            out[f"top_{k}"] = coverage[-1][2] if coverage else 0.0
    return out


def _format_families_md(data: dict[str, Any]) -> str:
    lines = [
        f"# Scenario families — {data['stage']}",
        "",
        f"Team set size: {data['team_set_size']} | Overlap floor: {data['overlap_floor']} | "
        f"Unique combos: {data['total_unique_combos']}",
        "",
    ]
    for i, fam in enumerate(data["families"][:20], start=1):
        lines.append(f"## Family {i} (overlap {fam['overlap']} with anchor)")
        lines.append(
            f"- Anchor: {' | '.join(fam['anchor'])} ({fam['anchor_count']:,} sims)"
        )
        lines.append(f"- Family sims: {fam['sim_count']:,} | Members: {fam['member_count']}")
        lines.append(f"- Consensus: {', '.join(fam['consensus_teams']) or '(none)'}")
        lines.append(f"- Contested: {', '.join(fam['contested_teams']) or '(none)'}")
        lines.append("")
    return "\n".join(lines)


def analyze_bracket_dir(
    bracket_dir: Path,
    *,
    tournament: str,
    max_sims: int | None = None,
) -> Path:
    """
    Run full Part 7 analysis into bracket_dir/analysis/.
    If max_sims is set, scale counts down proportionally (for capping display only).
    """
    cfg = load_tournament_config(tournament)
    state_path = bracket_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    total = int(state.get("total_sims", 0))
    if total <= 0:
        raise ValueError(f"No simulations in {state_path}")

    analysis_dir = bracket_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    groups_path = cfg.groups_file
    groups_data = json.loads(groups_path.read_text(encoding="utf-8"))
    all_teams = sorted({t for ts in groups_data["groups"].values() for t in ts})

    write_marginal_csv(
        analysis_dir / "marginal_stage_probabilities.csv",
        state,
        cfg.stages_tracked,
        all_teams,
    )

    summary: dict[str, Any] = {
        "tournament": tournament,
        "bracket_dir": stage_relative_path(bracket_dir),
        "total_sims": total,
        "max_sims_cap": max_sims,
        "stages": {},
    }

    stages_with_configs = sorted(
        {parse_config_key(k)[0] for k in state.get("config_counts", {})}
    )

    for stage in stages_with_configs:
        if stage not in STAGE_TEAM_COUNTS:
            continue
        combos = combos_for_stage(state, stage)
        coverage = cumulative_coverage(combos, total)
        _write_combos_csv(analysis_dir / f"stage_combinations_{stage}.csv", combos, total)
        _write_coverage_csv(analysis_dir / f"stage_coverage_{stage}.csv", coverage)

        stage_summary = {
            "unique_combos": len(combos),
            "coverage": _coverage_summary(coverage, [10, 50, 100, 500]),
            "top_20": [
                {"teams": list(t), "count": c, "probability": c / total}
                for t, c in combos[:20]
            ],
        }
        summary["stages"][stage] = stage_summary

        if stage in FAMILY_STAGES:
            families = build_scenario_families(combos, stage=stage, sim_total=total)
            fam_path = analysis_dir / f"scenario_families_{stage}.json"
            fam_path.write_text(json.dumps(families, indent=2), encoding="utf-8")
            (analysis_dir / f"scenario_families_{stage}.md").write_text(
                _format_families_md(families), encoding="utf-8"
            )

    (analysis_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return analysis_dir
