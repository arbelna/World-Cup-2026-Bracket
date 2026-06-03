from __future__ import annotations

import argparse
from pathlib import Path

from src.data_collection.core.manifest import sync_manifest
from src.data_collection.core.paths import resolve_collection_paths
from src.data_collection.pipeline.elo_confed import collect_confederations, collect_elo
from src.data_collection.pipeline.odds import (
    collect_odds_all,
    collect_odds_missing,
    generate_missing_template,
    match_odds,
)
from src.data_collection.pipeline.transfermarkt import (
    collect_transfermarkt,
    resolve_transfermarkt_from_existing,
)

DEFAULT_TM_DB_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.duckdb"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorldCup2026 Bracket data collection CLI")
    parser.add_argument(
        "--partition",
        choices=("legacy12", "wc2026"),
        required=True,
        help="Output partition (old 12 tournaments or WC2026).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Data_Collection root directory.",
    )
    parser.add_argument(
        "--sanity-check",
        action="store_true",
        help="Collect minimal data for wiring checks.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_elo = sub.add_parser("collect-elo", help="Collect Elo fixtures and ratings.")
    p_elo.set_defaults(func=lambda a: collect_elo(a.root, a.partition, sanity_check=a.sanity_check))

    p_conf = sub.add_parser("collect-confederations", help="Collect team confederations.")
    p_conf.set_defaults(func=lambda a: collect_confederations(a.root, a.partition))

    p_odds_all = sub.add_parser("collect-odds-all", help="Collect all OddsPortal odds by tournaments.")
    p_odds_all.add_argument("--odds-workers", type=int, default=2)
    p_odds_all.add_argument("--max-match-pages", type=int, default=0)
    p_odds_all.set_defaults(
        func=lambda a: collect_odds_all(
            a.root,
            a.partition,
            sanity_check=a.sanity_check,
            odds_workers=a.odds_workers,
            max_match_pages=a.max_match_pages or None,
        )
    )

    p_odds_missing = sub.add_parser(
        "collect-odds-missing",
        help="Collect OddsPortal only for URLs listed in missing_odds_manual.json.",
    )
    p_odds_missing.add_argument("--odds-workers", type=int, default=2)
    p_odds_missing.set_defaults(
        func=lambda a: collect_odds_missing(a.root, a.partition, odds_workers=a.odds_workers)
    )

    p_match = sub.add_parser("match-odds", help="Match raw odds to fixtures and regenerate unmatched list.")
    p_match.set_defaults(func=lambda a: match_odds(a.root, a.partition))

    p_missing_template = sub.add_parser(
        "generate-missing-template",
        help="Generate missing_odds_manual.json from fixtures not covered in matched odds.",
    )
    p_missing_template.set_defaults(func=lambda a: generate_missing_template(a.root, a.partition))

    p_tm = sub.add_parser(
        "collect-transfermarkt",
        help="Collect squads from Wikipedia and attach market values from DB then API fallback.",
    )
    p_tm.add_argument(
        "--skip-tm-api-backfill",
        action="store_true",
        help="Skip Transfermarkt API fallback pass for missing valuations.",
    )
    p_tm.add_argument(
        "--tm-db-url",
        default=DEFAULT_TM_DB_URL,
        help="URL to download/update transfermarkt-datasets.duckdb before collection.",
    )
    p_tm.set_defaults(
        func=lambda a: collect_transfermarkt(
            a.root,
            a.partition,
            skip_api_backfill=a.skip_tm_api_backfill,
            tm_db_url=a.tm_db_url,
        )
    )
    p_tm_update = sub.add_parser(
        "update-tm-db",
        help="Download/update transfermarkt-datasets.duckdb into data root.",
    )
    p_tm_update.add_argument(
        "--tm-db-url",
        default=DEFAULT_TM_DB_URL,
        help="URL to download/update transfermarkt-datasets.duckdb.",
    )
    p_tm_update.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if local DB already exists.",
    )

    def _update_tm_db(args: argparse.Namespace) -> None:
        from src.data_collection.core.paths import resolve_collection_paths
        from src.data_collection.pipeline.transfermarkt import _maybe_update_tm_db

        paths = resolve_collection_paths(args.root, args.partition)
        _maybe_update_tm_db(paths.tm_db_path, args.tm_db_url, force=args.force)

    p_tm_update.set_defaults(func=_update_tm_db)

    p_tm_resolve = sub.add_parser(
        "resolve-transfermarkt-existing",
        help="Resolve values for existing squads only (no Wikipedia recollection).",
    )
    p_tm_resolve.add_argument(
        "--skip-tm-api-backfill",
        action="store_true",
        help="Skip Transfermarkt API fallback pass.",
    )
    p_tm_resolve.add_argument(
        "--tm-db-url",
        default=DEFAULT_TM_DB_URL,
        help="URL to download/update transfermarkt-datasets.duckdb before resolving.",
    )
    p_tm_resolve.set_defaults(
        func=lambda a: resolve_transfermarkt_from_existing(
            a.root,
            a.partition,
            skip_api_backfill=a.skip_tm_api_backfill,
            tm_db_url=a.tm_db_url,
        )
    )

    p_sync_manifest = sub.add_parser(
        "sync-manifest",
        help="Refresh manifest counts from existing output files (no re-collection).",
    )

    def _sync_manifest(args: argparse.Namespace) -> None:
        paths = resolve_collection_paths(args.root, args.partition)
        manifest = sync_manifest(paths)
        print(f"[MANIFEST] Synced partition={args.partition} counts={manifest.get('counts')}")

    p_sync_manifest.set_defaults(func=_sync_manifest)

    p_all = sub.add_parser("run-all", help="Run all collection stages for a partition.")
    p_all.add_argument("--odds-workers", type=int, default=2)
    p_all.add_argument("--max-match-pages", type=int, default=0)
    p_all.add_argument("--skip-odds", action="store_true")
    p_all.add_argument("--skip-transfermarkt", action="store_true")

    def _run_all(args: argparse.Namespace) -> None:
        collect_elo(args.root, args.partition, sanity_check=args.sanity_check)
        collect_confederations(args.root, args.partition)
        if not args.skip_odds:
            collect_odds_all(
                args.root,
                args.partition,
                sanity_check=args.sanity_check,
                odds_workers=args.odds_workers,
                max_match_pages=args.max_match_pages or None,
            )
            match_odds(args.root, args.partition)
            generate_missing_template(args.root, args.partition)
        if not args.skip_transfermarkt:
            collect_transfermarkt(args.root, args.partition)
        paths = resolve_collection_paths(args.root, args.partition)
        manifest = sync_manifest(paths)
        print(f"[MANIFEST] run-all finalized partition={args.partition} counts={manifest.get('counts')}")

    p_all.set_defaults(func=_run_all)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
