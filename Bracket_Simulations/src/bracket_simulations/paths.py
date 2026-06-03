from __future__ import annotations

from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = STAGE_ROOT / "config"
DATA_INPUT = STAGE_ROOT / "data" / "input"
DATA_OUTPUT = STAGE_ROOT / "data" / "output" / "simulations"
MATCH_DATASET = DATA_INPUT / "match_dataset.json"
FIXTURES_STATS = DATA_INPUT / "fixtures_stats.json"
OLD_STATS_DIR = DATA_INPUT / "old_stats" / "worldcup-master"


def stage_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(STAGE_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
