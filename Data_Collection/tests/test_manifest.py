from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.data_collection.core.manifest import (
    STAGE_COUNT_KEYS,
    counts_from_outputs,
    sync_manifest,
    write_manifest,
)
from src.data_collection.core.paths import resolve_collection_paths


class ManifestAutoSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.paths = resolve_collection_paths(self.root, "legacy12")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_write_manifest_overwrites_counts_from_disk(self) -> None:
        self.paths.fixtures_path.write_text(json.dumps([{"match_id": "a"}, {"match_id": "b"}]), encoding="utf-8")
        self.paths.team_ratings_path.write_text(json.dumps([{"team": "x"}]), encoding="utf-8")

        write_manifest(
            self.paths.manifest_path,
            stage="collect_elo",
            partition="legacy12",
            tournament_ids=["world-cup-2022"],
            counts={"fixtures": 999, "team_ratings": 999},
        )

        manifest = json.loads(self.paths.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["counts"]["fixtures"], 2)
        self.assertEqual(manifest["counts"]["team_ratings"], 1)
        self.assertEqual(manifest["stages"]["collect_elo"]["counts"]["fixtures"], 2)

    def test_sync_manifest_updates_all_known_stages(self) -> None:
        self.paths.odds_raw_path.write_text(json.dumps([{}] * 5), encoding="utf-8")
        self.paths.odds_matched_path.write_text(json.dumps([{}] * 4), encoding="utf-8")
        self.paths.odds_unmatched_path.write_text(json.dumps([]), encoding="utf-8")

        write_manifest(
            self.paths.manifest_path,
            stage="collect_odds_all",
            partition="legacy12",
            tournament_ids=["world-cup-2022"],
            counts={"oddsportal_raw": 1},
        )
        write_manifest(
            self.paths.manifest_path,
            stage="match_odds",
            partition="legacy12",
            tournament_ids=["world-cup-2022"],
            counts={"matched_odds": 1, "unmatched_odds": 1, "dropped_invalid_odds": 0},
        )

        manifest = sync_manifest(self.paths)
        self.assertEqual(manifest["stages"]["collect_odds_all"]["counts"]["oddsportal_raw"], 5)
        self.assertEqual(manifest["stages"]["match_odds"]["counts"]["matched_odds"], 4)
        self.assertEqual(manifest["stages"]["match_odds"]["counts"]["dropped_invalid_odds"], 1)

    def test_counts_from_outputs_squad_and_odds_keys(self) -> None:
        squads = {"player_count": 10, "tournaments": []}
        with_value = {
            "market_value_summary": {
                "valued_players": 8,
                "unmatched_players": 2,
                "matched_players": 9,
            },
            "tournaments": [],
        }
        unmatched = {"players": [{}, {}]}
        (self.paths.market_value_dir / "tournament_squads.json").write_text(
            json.dumps(squads), encoding="utf-8"
        )
        (self.paths.market_value_dir / "tournament_squads_with_value.json").write_text(
            json.dumps(with_value), encoding="utf-8"
        )
        (self.paths.market_value_dir / "tournament_squads_unmatched_players.json").write_text(
            json.dumps(unmatched), encoding="utf-8"
        )

        counts = counts_from_outputs(self.paths)
        self.assertEqual(counts["squads_players"], 10)
        self.assertEqual(counts["valued_players"], 8)
        self.assertEqual(counts["unmatched_players"], 2)

    def test_stage_count_keys_cover_transfermarkt_stages(self) -> None:
        for stage in ("collect_transfermarkt", "resolve_transfermarkt_from_existing"):
            self.assertIn(stage, STAGE_COUNT_KEYS)
            self.assertIn("valued_players", STAGE_COUNT_KEYS[stage])


if __name__ == "__main__":
    unittest.main()
