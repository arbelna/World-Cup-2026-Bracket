from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CollectionPaths:
    root: Path
    partition: str
    base_dir: Path
    data_dir: Path
    market_value_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.base_dir / "manifest.json"

    @property
    def fixtures_path(self) -> Path:
        return self.base_dir / "fixtures_stats.json"

    @property
    def team_ratings_path(self) -> Path:
        return self.base_dir / "teams_ratings.json"

    @property
    def team_confederations_path(self) -> Path:
        return self.base_dir / "team_confederations.json"

    @property
    def odds_raw_path(self) -> Path:
        return self.base_dir / "oddsportal_raw_odds.json"

    @property
    def odds_matched_path(self) -> Path:
        return self.base_dir / "matched_odds.json"

    @property
    def odds_unmatched_path(self) -> Path:
        return self.base_dir / "unmatched_odds.json"

    @property
    def missing_manual_path(self) -> Path:
        return self.base_dir / "missing_odds_manual.json"

    @property
    def tm_db_path(self) -> Path:
        return self.data_dir / "transfermarkt-datasets.duckdb"


def resolve_collection_paths(root: Path, partition: str) -> CollectionPaths:
    data_dir = root / "data"
    base = data_dir / partition
    market = base
    data_dir.mkdir(parents=True, exist_ok=True)
    base.mkdir(parents=True, exist_ok=True)
    market.mkdir(parents=True, exist_ok=True)
    return CollectionPaths(
        root=root,
        partition=partition,
        base_dir=base,
        data_dir=data_dir,
        market_value_dir=market,
    )
