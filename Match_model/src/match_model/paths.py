from __future__ import annotations

from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parents[2]

INPUT_ROOT = STAGE_ROOT / "data" / "input"
LEGACY12_DIR = INPUT_ROOT / "legacy12"
OLD_STATS_DIR = STAGE_ROOT / "data" / "reference" / "old_stats"

OUTPUT_ROOT = STAGE_ROOT / "data" / "output"
DATASETS_DIR = OUTPUT_ROOT / "datasets"
EXPERIMENTS_DIR = OUTPUT_ROOT / "experiments"

DEFAULT_DATASET_PATH = DATASETS_DIR / "match_dataset.json"
