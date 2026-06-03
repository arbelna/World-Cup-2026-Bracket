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
    parser.add_argument("--skip-tm-api-backfill", action="store_true")
    parser.add_argument("--tm-db-url", default=None)
    args = parser.parse_args()
    argv = ["--partition", args.partition, "collect-transfermarkt"]
    if args.skip_tm_api_backfill:
        argv.append("--skip-tm-api-backfill")
    if args.tm_db_url:
        argv.extend(["--tm-db-url", args.tm_db_url])
    main(argv)
