"""
Export dashboard JSON files from the latest WC2026 simulation runs.

Usage:
    python export_dashboard_json.py [--repo-root PATH]

Outputs:
    docs/data/market.json
    docs/data/model.json
    docs/data/market_sim_matrix.npz
    docs/data/model_sim_matrix.npz
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Group / confederation mapping (uses exact team names from wc2026_groups.json)
# ---------------------------------------------------------------------------

GROUPS: dict[str, list[str]] = {
    "A": ["Czechia", "Mexico", "South Africa", "South Korea"],
    "B": ["Bosnia and Herzegovina", "Canada", "Qatar", "Switzerland"],
    "C": ["Brazil", "Haiti", "Morocco", "Scotland"],
    "D": ["Australia", "Paraguay", "Turkey", "United States"],
    "E": ["Curaçao", "Ecuador", "Germany", "Ivory Coast"],
    "F": ["Japan", "Netherlands", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Cape Verde", "Saudi Arabia", "Spain", "Uruguay"],
    "I": ["France", "Iraq", "Norway", "Senegal"],
    "J": ["Algeria", "Argentina", "Austria", "Jordan"],
    "K": ["Colombia", "DR Congo", "Portugal", "Uzbekistan"],
    "L": ["Croatia", "England", "Ghana", "Panama"],
}

CONFEDERATIONS: dict[str, str] = {
    # UEFA
    "Austria": "UEFA",
    "Belgium": "UEFA",
    "Bosnia and Herzegovina": "UEFA",
    "Croatia": "UEFA",
    "Czechia": "UEFA",
    "England": "UEFA",
    "France": "UEFA",
    "Germany": "UEFA",
    "Netherlands": "UEFA",
    "Norway": "UEFA",
    "Portugal": "UEFA",
    "Scotland": "UEFA",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Switzerland": "UEFA",
    "Turkey": "UEFA",
    # CONMEBOL
    "Argentina": "CONMEBOL",
    "Brazil": "CONMEBOL",
    "Colombia": "CONMEBOL",
    "Ecuador": "CONMEBOL",
    "Paraguay": "CONMEBOL",
    "Uruguay": "CONMEBOL",
    # AFC
    "Australia": "AFC",
    "Iran": "AFC",
    "Iraq": "AFC",
    "Japan": "AFC",
    "Jordan": "AFC",
    "Qatar": "AFC",
    "Saudi Arabia": "AFC",
    "South Korea": "AFC",
    "Uzbekistan": "AFC",
    # CAF
    "Algeria": "CAF",
    "Cape Verde": "CAF",
    "DR Congo": "CAF",
    "Egypt": "CAF",
    "Ghana": "CAF",
    "Ivory Coast": "CAF",
    "Morocco": "CAF",
    "Senegal": "CAF",
    "South Africa": "CAF",
    "Tunisia": "CAF",
    # CONCACAF
    "Canada": "CONCACAF",
    "Curaçao": "CONCACAF",
    "Haiti": "CONCACAF",
    "Mexico": "CONCACAF",
    "Panama": "CONCACAF",
    "United States": "CONCACAF",
    # OFC
    "New Zealand": "OFC",
}

# Build reverse lookup: team -> group
TEAM_GROUP: dict[str, str] = {
    team: grp for grp, teams in GROUPS.items() for team in teams
}

STAGES_EXPORT = ["R32", "R16", "QF", "SF", "final", "winner"]


def find_best_run_dir(base_dir: Path, mode: str) -> tuple[Path, int] | None:
    """Return (dir, total_sims) for the run with most simulations."""
    mode_dir = base_dir / mode
    if not mode_dir.is_dir():
        return None
    best_dir: Path | None = None
    best_sims = -1
    for fp_dir in mode_dir.iterdir():
        if not fp_dir.is_dir():
            continue
        state_path = fp_dir / "state.json"
        if not state_path.exists():
            continue
        # Read only beginning to get total_sims (state.json may be large)
        total_sims = _read_total_sims(state_path)
        if total_sims > best_sims:
            best_sims = total_sims
            best_dir = fp_dir
    if best_dir is None:
        return None
    return best_dir, best_sims


def _read_total_sims(state_path: Path) -> int:
    """Read total_sims from state.json without loading the whole file."""
    try:
        # Read first 4KB — total_sims is always near the top
        chunk = state_path.read_bytes()[:4096].decode("utf-8", errors="replace")
        # Try full parse first (fast for small files)
        try:
            data = json.loads(chunk)
            return int(data.get("total_sims", 0))
        except json.JSONDecodeError:
            pass
        # Partial file: scan for the key
        import re
        m = re.search(r'"total_sims"\s*:\s*(\d+)', chunk)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0


def read_team_probs(csv_path: Path) -> dict[str, dict[str, float]]:
    """Parse team_stage_probabilities.csv -> {team: {stage: p_at_least}}"""
    result: dict[str, dict[str, float]] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row["team"]
            probs: dict[str, float] = {}
            for stage in STAGES_EXPORT:
                col = f"p_at_least_{stage}"
                probs[stage] = float(row.get(col, 0.0))
            result[team] = probs
    return result


def read_stage_configs(csv_path: Path) -> dict[str, list[dict]]:
    """Parse stage_config_probabilities.csv -> {stage: [{teams, probability, rank}]}"""
    result: dict[str, list[dict]] = {s: [] for s in STAGES_EXPORT if s != "R32"}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage = row["stage"]
            if stage not in result:
                continue
            teams = row["teams"].split("|")
            result[stage].append({
                "teams": teams,
                "probability": float(row["probability"]),
                "rank": int(row["rank"]),
            })
    return result


def build_json(
    mode: str,
    run_dir: Path,
    total_sims: int,
    sim_matrix_url: str,
) -> dict:
    probs_path = run_dir / "team_stage_probabilities.csv"
    configs_path = run_dir / "stage_config_probabilities.csv"

    team_probs = read_team_probs(probs_path)
    top_configs = read_stage_configs(configs_path)

    teams_list = []
    for team in sorted(team_probs.keys()):
        group = TEAM_GROUP.get(team)
        confederation = CONFEDERATIONS.get(team)
        if group is None:
            print(f"WARNING: unmapped team '{team}' — no group found", file=sys.stderr)
            group = "?"
        if confederation is None:
            print(f"WARNING: unmapped team '{team}' — no confederation found", file=sys.stderr)
            confederation = "?"
        teams_list.append({
            "name": team,
            "group": group,
            "confederation": confederation,
            "probs": team_probs[team],
        })

    # Read sidecar if available
    sidecar_path = run_dir / "sim_matrix_index.json"
    if sidecar_path.exists():
        sim_matrix_index = json.loads(sidecar_path.read_text(encoding="utf-8"))
    else:
        sim_matrix_index = {
            "teams": sorted(team_probs.keys()),
            "stages": STAGES_EXPORT,
        }

    return {
        "meta": {
            "tournament": "wc2026",
            "mode": mode,
            "n_sims": total_sims,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "stages": STAGES_EXPORT,
        "teams": teams_list,
        "top_configs": top_configs,
        "sim_matrix_url": sim_matrix_url,
        "sim_matrix_index": sim_matrix_index,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export dashboard JSON from WC2026 simulation runs")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to repo root (default: two levels up from this script)",
    )
    args = parser.parse_args(argv)

    if args.repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    else:
        repo_root = Path(args.repo_root).resolve()

    sim_base = repo_root / "data" / "output" / "simulations" / "wc2026"

    # Support docs/ at repo root (for GitHub Pages) or inside Bracket_Simulations/
    repo_git_root = repo_root.parent  # one level up from Bracket_Simulations/
    root_docs = repo_git_root / "docs"
    local_docs = repo_root / "docs"
    docs_data = (root_docs if root_docs.exists() else local_docs) / "data"
    docs_data.mkdir(parents=True, exist_ok=True)

    modes = ["market_all", "model_all"]
    mode_prefix = {"market_all": "market", "model_all": "model"}

    for mode in modes:
        prefix = mode_prefix[mode]
        result = find_best_run_dir(sim_base, mode)
        if result is None:
            print(f"WARNING: no simulation run found for mode '{mode}'", file=sys.stderr)
            continue

        run_dir, total_sims = result
        print(f"[{mode}] best run: {run_dir.name}  ({total_sims:,} sims)")

        sim_matrix_url = f"data/{prefix}_sim_matrix.npz"
        payload = build_json(mode, run_dir, total_sims, sim_matrix_url)

        out_json = docs_data / f"{prefix}.json"
        out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  Wrote {out_json}")

        # Export sim_matrix.npz (bit-packed) if it exists.
        # Packing the boolean matrix with np.packbits cuts the download
        # ~40% and the in-browser memory footprint ~8x, while remaining
        # lossless. The dashboard JS detects the 'packed'/'shape' keys.
        npz_src = run_dir / "sim_matrix.npz"
        npz_dst = docs_data / f"{prefix}_sim_matrix.npz"
        if npz_src.exists():
            with np.load(npz_src) as src_npz:
                key = src_npz.files[0]
                matrix = src_npz[key]
            matrix = np.ascontiguousarray(matrix.astype(bool))
            packed = np.packbits(matrix)  # C-order, MSB-first
            shape = np.array(matrix.shape, dtype=np.int32)
            np.savez_compressed(npz_dst, packed=packed, shape=shape)
            print(
                f"  Packed sim_matrix.npz {matrix.shape} -> {npz_dst} "
                f"({npz_dst.stat().st_size/1e6:.2f} MB)"
            )
        else:
            print(
                f"  NOTE: {npz_src} not found — run simulations with the "
                f"updated pipeline to generate it"
            )

    print("Done.")


if __name__ == "__main__":
    main()
