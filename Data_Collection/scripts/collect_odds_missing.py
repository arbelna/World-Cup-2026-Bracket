from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main_cli import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", choices=("legacy12", "wc2026"), required=True)
    parser.add_argument("--odds-workers", type=int, default=2)
    args = parser.parse_args()
    main(
        [
            "--partition",
            args.partition,
            "collect-odds-missing",
            "--odds-workers",
            str(args.odds_workers),
        ]
    )
