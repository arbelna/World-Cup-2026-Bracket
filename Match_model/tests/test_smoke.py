from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

STAGE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = STAGE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from match_model.paths import DEFAULT_DATASET_PATH, EXPERIMENTS_DIR, LEGACY12_DIR, OLD_STATS_DIR, STAGE_ROOT as MODULE_STAGE_ROOT
from match_model.results_report import write_results_markdown


class MatchModelSmokeTest(unittest.TestCase):
    def test_default_paths_stay_inside_stage_root(self) -> None:
        self.assertEqual(MODULE_STAGE_ROOT, STAGE_ROOT)
        for path in (LEGACY12_DIR, OLD_STATS_DIR, DEFAULT_DATASET_PATH, EXPERIMENTS_DIR):
            self.assertTrue(path.is_relative_to(STAGE_ROOT))

    def test_results_report_uses_repo_relative_repro_steps(self) -> None:
        self.assertTrue(DEFAULT_DATASET_PATH.exists(), "Committed dataset is required for this smoke test")
        self.assertTrue(EXPERIMENTS_DIR.exists(), "Committed experiment outputs are required for this smoke test")

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "results.md"
            write_results_markdown(
                experiments_dir=EXPERIMENTS_DIR,
                dataset_path=DEFAULT_DATASET_PATH,
                output_path=out_path,
            )
            text = out_path.read_text(encoding="utf-8")

        self.assertIn("Cross-entropy (CE)", text)
        self.assertIn("delta Brier vs Elo", text)
        self.assertNotIn("Target oracle CE", text)
        self.assertIn("## 0. Experiment pipeline", text)
        self.assertIn("## 3. Group stage vs knockout matches", text)
        self.assertNotIn("![", text)
        self.assertIn("## 4. Highest cross-entropy predictions (CatBoost)", text)
        self.assertIn("| # | Match | Stage | Actual 90m | Market top call | Model top call | CE | Brier |", text)
        self.assertNotIn("## 5. Interpretation notes", text)
        self.assertNotIn("## 5. Reproduce", text)
        self.assertNotIn("python main_cli.py run-all", text)
        self.assertIn("## 5. WC2026 explicit holdout (train legacy12, test WC2026)", text)
        self.assertIn("reasonable inputs for the bracket simulation stage", text)
        self.assertNotRegex(text, r"[A-Z]:\\")

        section4 = text.split("## 4. Highest cross-entropy predictions (CatBoost)", 1)[1]
        section4 = section4.split("## 5. WC2026 explicit holdout", 1)[0]
        rows = [
            line
            for line in section4.splitlines()
            if line.startswith("| ") and " vs " in line and "Market top call" not in line
        ]
        self.assertEqual(len(rows), 10)


if __name__ == "__main__":
    unittest.main()
