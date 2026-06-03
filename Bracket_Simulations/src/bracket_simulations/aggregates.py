from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_KEY_SEP = "|||"


def config_tuple_key(stage: str, teams: tuple[str, ...]) -> str:
    return f"{stage}{CONFIG_KEY_SEP}{'|'.join(teams)}"


def parse_config_key(key: str) -> tuple[str, tuple[str, ...]]:
    stage, teams_str = key.split(CONFIG_KEY_SEP, 1)
    if teams_str:
        return stage, tuple(teams_str.split("|"))
    return stage, ()


def settings_fingerprint(*, tournament: str, mode: str, alphas: dict[str, float]) -> str:
    payload = json.dumps({"tournament": tournament, "mode": mode, "alphas": alphas}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def resolve_bracket_output_dir(tournament_output_dir: Path, *, mode: str, settings_fp: str) -> Path:
    return tournament_output_dir / mode / settings_fp


def write_settings_json(path: Path, *, tournament: str, mode: str, alphas: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tournament": tournament,
        "mode": mode,
        "alphas": alphas,
        "settings_fingerprint": settings_fingerprint(tournament=tournament, mode=mode, alphas=alphas),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"total_sims": 0, "reach_counts": {}, "config_counts": {}, "settings_fingerprint": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state_atomic(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError as exc:
        try:
            path.write_text(content, encoding="utf-8")
        except OSError:
            raise exc from None
        tmp.unlink(missing_ok=True)
        logger.warning("Could not atomically replace %s (%s); updated in place.", path.name, exc)


def merge_reach_counts(
    state: dict[str, Any],
    batch: list[dict[str, str]],
    stages_tracked: list[str],
) -> None:
    counts = state.setdefault("reach_counts", {})
    for team_stages in batch:
        for team, stage in team_stages.items():
            if stage not in stages_tracked:
                continue
            team_counts = counts.setdefault(team, {})
            team_counts[stage] = int(team_counts.get(stage, 0)) + 1


def merge_config_counts(
    state: dict[str, Any],
    batch: list[dict[str, tuple[str, ...]]],
) -> None:
    counts = state.setdefault("config_counts", {})
    for participants in batch:
        for stage, teams in participants.items():
            key = config_tuple_key(stage, teams)
            counts[key] = int(counts.get(key, 0)) + 1


def exit_and_cumulative_probs(
    team_counts: dict[str, int],
    stages_tracked: list[str],
    total: int,
) -> tuple[dict[str, float], dict[str, float]]:
    if total <= 0:
        return {}, {}
    exit_p = {stage: int(team_counts.get(stage, 0)) / total for stage in stages_tracked}
    cumulative_p = {}
    for i, stage in enumerate(stages_tracked):
        cumulative_p[stage] = sum(int(team_counts.get(s, 0)) for s in stages_tracked[i:]) / total
    return exit_p, cumulative_p


def write_probabilities_csv(
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
        exit_cols = [f"p_exit_{s}" for s in stages_tracked]
        reach_cols = [f"p_at_least_{s}" for s in stages_tracked]
        writer.writerow(["team", *exit_cols, *reach_cols])
        for team in sorted(all_teams):
            tc = counts.get(team, {})
            exit_p, cumulative_p = exit_and_cumulative_probs(tc, stages_tracked, total)
            row = [team]
            row.extend(f"{exit_p[stage]:.6f}" for stage in stages_tracked)
            row.extend(f"{cumulative_p[stage]:.6f}" for stage in stages_tracked)
            writer.writerow(row)


def write_stage_config_csv(
    path: Path,
    state: dict[str, Any],
    *,
    top_n: int = 50,
) -> None:
    total = int(state.get("total_sims", 0))
    config_counts: dict[str, int] = state.get("config_counts", {})
    path.parent.mkdir(parents=True, exist_ok=True)

    by_stage: dict[str, list[tuple[tuple[str, ...], int]]] = {}
    for key, count in config_counts.items():
        stage, teams = parse_config_key(key)
        by_stage.setdefault(stage, []).append((teams, int(count)))

    rows: list[tuple[str, str, int, float, int]] = []
    for stage in sorted(by_stage.keys()):
        ranked = sorted(by_stage[stage], key=lambda x: x[1], reverse=True)
        for rank, (teams, count) in enumerate(ranked[:top_n], start=1):
            prob = count / total if total > 0 else 0.0
            rows.append((stage, "|".join(teams), count, prob, rank))

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stage", "teams", "count", "probability", "rank"])
        for row in rows:
            writer.writerow([row[0], row[1], row[2], f"{row[3]:.8f}", row[4]])


def config_probability(state: dict[str, Any], stage: str, teams: tuple[str, ...]) -> float:
    total = int(state.get("total_sims", 0))
    if total <= 0:
        return 0.0
    key = config_tuple_key(stage, tuple(sorted(teams)))
    count = int(state.get("config_counts", {}).get(key, 0))
    return count / total


def config_rank(state: dict[str, Any], stage: str, teams: tuple[str, ...]) -> int:
    actual_key = config_tuple_key(stage, tuple(sorted(teams)))
    config_counts: dict[str, int] = state.get("config_counts", {})
    prefix = stage + CONFIG_KEY_SEP
    ranked = sorted(
        ((k, v) for k, v in config_counts.items() if k.startswith(prefix)),
        key=lambda x: x[1],
        reverse=True,
    )
    for rank, (key, _) in enumerate(ranked, start=1):
        if key == actual_key:
            return rank
    return len(ranked) + 1


def top_config_for_stage(state: dict[str, Any], stage: str) -> tuple[tuple[str, ...], float] | None:
    config_counts: dict[str, int] = state.get("config_counts", {})
    total = int(state.get("total_sims", 0))
    if total <= 0:
        return None
    best_key = None
    best_count = -1
    for key, count in config_counts.items():
        if not key.startswith(stage + CONFIG_KEY_SEP):
            continue
        if count > best_count:
            best_count = count
            best_key = key
    if best_key is None:
        return None
    _, teams = parse_config_key(best_key)
    return teams, best_count / total


def save_run_metadata(path: Path, meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
