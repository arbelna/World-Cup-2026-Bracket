from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.data_collection.config.tournaments import tournaments_for_partition
from src.data_collection.core.manifest import counts_from_outputs
from src.data_collection.core.paths import resolve_collection_paths

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY12 = PROJECT_ROOT / "data" / "legacy12"


def _legacy12_available() -> bool:
    required = (
        LEGACY12 / "manifest.json",
        LEGACY12 / "fixtures_stats.json",
        LEGACY12 / "tournament_squads_with_value.json",
        LEGACY12 / "matched_odds.json",
    )
    return all(path.exists() for path in required)


@unittest.skipUnless(_legacy12_available(), "legacy12 collection outputs not present")
class Legacy12CollectionOutputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = resolve_collection_paths(PROJECT_ROOT, "legacy12")
        cls.manifest = json.loads(cls.paths.manifest_path.read_text(encoding="utf-8"))
        cls.derived = counts_from_outputs(cls.paths)

    def test_manifest_last_stage_present(self) -> None:
        self.assertIn(self.manifest.get("last_stage"), self.manifest.get("stages", {}))

    def test_manifest_counts_match_disk_outputs(self) -> None:
        last_stage = self.manifest["last_stage"]
        stage_counts = self.manifest["stages"][last_stage]["counts"]
        top_counts = self.manifest["counts"]

        for key, expected in self.derived.items():
            if key in top_counts:
                self.assertEqual(
                    top_counts[key],
                    expected,
                    f"top-level manifest count {key!r} drifted from on-disk outputs",
                )
            if key in stage_counts:
                self.assertEqual(
                    stage_counts[key],
                    expected,
                    f"stage {last_stage!r} count {key!r} drifted from on-disk outputs",
                )

    def test_elo_fixture_and_rating_counts(self) -> None:
        fixtures = json.loads(self.paths.fixtures_path.read_text(encoding="utf-8"))
        ratings = json.loads(self.paths.team_ratings_path.read_text(encoding="utf-8"))
        self.assertEqual(self.derived["fixtures"], len(fixtures))
        self.assertEqual(self.derived["team_ratings"], len(ratings))
        self.assertGreater(self.derived["fixtures"], 500)

    def test_odds_accounting(self) -> None:
        raw = json.loads(self.paths.odds_raw_path.read_text(encoding="utf-8"))
        matched = json.loads(self.paths.odds_matched_path.read_text(encoding="utf-8"))
        unmatched = json.loads(self.paths.odds_unmatched_path.read_text(encoding="utf-8"))
        dropped = self.derived["dropped_invalid_odds"]
        self.assertEqual(len(raw), len(matched) + len(unmatched) + dropped)

    def test_squad_player_accounting(self) -> None:
        squads = json.loads((self.paths.market_value_dir / "tournament_squads.json").read_text(encoding="utf-8"))
        with_value = json.loads(
            (self.paths.market_value_dir / "tournament_squads_with_value.json").read_text(encoding="utf-8")
        )
        unmatched = json.loads(
            (self.paths.market_value_dir / "tournament_squads_unmatched_players.json").read_text(encoding="utf-8")
        )

        total = squads["player_count"]
        valued = self.derived["valued_players"]
        unmatched_count = len(unmatched["players"])

        self.assertEqual(with_value["player_count"], total)
        self.assertEqual(self.derived["unmatched_players"], unmatched_count)
        self.assertEqual(valued + unmatched_count, total)

    def test_legacy12_tournament_count(self) -> None:
        squads = json.loads((self.paths.market_value_dir / "tournament_squads.json").read_text(encoding="utf-8"))
        expected = len(tournaments_for_partition("legacy12"))
        self.assertEqual(squads["tournament_count"], expected)


class TournamentConfigTest(unittest.TestCase):
    def test_legacy12_has_twelve_tournaments(self) -> None:
        self.assertEqual(len(tournaments_for_partition("legacy12")), 12)

    def test_wc2026_has_one_tournament(self) -> None:
        self.assertEqual(len(tournaments_for_partition("wc2026")), 1)


if __name__ == "__main__":
    unittest.main()
