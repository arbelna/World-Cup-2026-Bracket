from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = STAGE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from match_model.dataset_builder import build_match_dataset
from match_model.export import write_loto_outputs
from match_model.loto import run_holdout_evaluation, run_loto_evaluation
from match_model.paths import (
    DEFAULT_DATASET_PATH,
    EXPERIMENTS_DIR,
    LEGACY12_DIR,
    OLD_STATS_DIR,
)


def cmd_build_dataset(args: argparse.Namespace) -> int:
    collection_dir = Path(args.collection_dir)
    old_stats_dir = Path(args.old_stats_dir)
    out_path = Path(args.output)

    dataset, summary = build_match_dataset(
        collection_dir=collection_dir,
        old_stats_dir=old_stats_dir,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")

    summary_path = out_path.with_name("match_dataset_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {len(dataset)} matches to {out_path}")
    print(f"Summary: {summary_path}")
    return 0


def cmd_run_loto(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    output_dir = Path(args.output_dir)
    payload = run_loto_evaluation(
        dataset_path,
        show_progress=not args.quiet,
        random_seed=args.seed,
    )
    paths = write_loto_outputs(
        payload,
        output_dir,
        output_prefix=args.prefix,
        dataset_path=Path(args.dataset),
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    build_args = argparse.Namespace(
        collection_dir=args.collection_dir,
        old_stats_dir=args.old_stats_dir,
        output=args.dataset,
    )
    cmd_build_dataset(build_args)
    loto_args = argparse.Namespace(
        dataset=args.dataset,
        output_dir=args.output_dir,
        quiet=args.quiet,
        seed=args.seed,
        prefix=args.prefix,
    )
    return cmd_run_loto(loto_args)


def cmd_run_holdout(args: argparse.Namespace) -> int:
    train_dataset = Path(args.train_dataset)
    test_dataset = Path(args.test_dataset)
    output_dir = Path(args.output_dir)
    payload = run_holdout_evaluation(
        train_dataset_path=train_dataset,
        test_dataset_path=test_dataset,
        held_out_competition=args.held_out_competition,
        show_progress=not args.quiet,
        random_seed=args.seed,
    )
    paths = write_loto_outputs(
        payload,
        output_dir,
        output_prefix=args.prefix,
        dataset_path=train_dataset,
        write_results_md=False,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorldCup2026 Bracket Match_model stage")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build-dataset", help="Build match_dataset.json from legacy12")
    p_build.add_argument("--collection-dir", default=str(LEGACY12_DIR))
    p_build.add_argument("--old-stats-dir", default=str(OLD_STATS_DIR))
    p_build.add_argument("--output", default=str(DEFAULT_DATASET_PATH))
    p_build.set_defaults(func=cmd_build_dataset)

    p_loto = sub.add_parser("run-loto", help="Run LOTO CatBoost + baselines")
    p_loto.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    p_loto.add_argument("--output-dir", default=str(EXPERIMENTS_DIR))
    p_loto.add_argument("--prefix", default="loto_eval")
    p_loto.add_argument("--seed", type=int, default=42)
    p_loto.add_argument("--quiet", action="store_true")
    p_loto.set_defaults(func=cmd_run_loto)

    p_all = sub.add_parser("run-all", help="Build dataset then run LOTO")
    p_all.add_argument("--collection-dir", default=str(LEGACY12_DIR))
    p_all.add_argument("--old-stats-dir", default=str(OLD_STATS_DIR))
    p_all.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    p_all.add_argument("--output-dir", default=str(EXPERIMENTS_DIR))
    p_all.add_argument("--prefix", default="loto_eval")
    p_all.add_argument("--seed", type=int, default=42)
    p_all.add_argument("--quiet", action="store_true")
    p_all.set_defaults(func=cmd_run_all)

    p_holdout = sub.add_parser("run-holdout", help="Run explicit train/test evaluation split")
    p_holdout.add_argument("--train-dataset", default=str(DEFAULT_DATASET_PATH))
    p_holdout.add_argument("--test-dataset", required=True)
    p_holdout.add_argument("--held-out-competition", default="World Cup 2026")
    p_holdout.add_argument("--output-dir", default=str(EXPERIMENTS_DIR))
    p_holdout.add_argument("--prefix", default="wc2026_holdout_eval")
    p_holdout.add_argument("--seed", type=int, default=42)
    p_holdout.add_argument("--quiet", action="store_true")
    p_holdout.set_defaults(func=cmd_run_holdout)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
