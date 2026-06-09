# WorldCup2026 Bracket - Match_model

Stage 2 of the local pipeline: build the modeling dataset and run leave-one-tournament-out (LOTO) evaluation for the CatBoost `core7` model against predictive baselines. Here, `core7` means the committed seven-feature core feature set listed below.

## Scope

- Build `match_dataset.json` from committed historical inputs plus vendored `old_stats` reference files.
- Run LOTO evaluation for:
  - `catboost_loto_core7`
  - `baseline__elo`: a rating-only baseline built from the tournament-start Elo gap
  - `baseline__marginal`: the unconditional historical 1X2 distribution with no match-specific inputs
  - `baseline__market_dispersion`: a market-aware reference baseline that uses bookmaker-price dispersion and is closer to a calibration reference than a fair standalone predictor
- Write plots and a human-readable report to `results.md`.

This stage is self-contained inside `WorldCup2026 Bracket`. Its sync script pulls collection inputs from the sibling `Data_Collection` folder only. The `old_stats` reference tree is vendored directly in this stage.

## Model inputs

The seven committed model features are built in `src/match_model/dataset_builder.py`:

| Feature | Meaning |
|------|---------|
| `elo_diff` | tournament-start Elo gap, team A minus team B |
| `stage_binary` | `1` for group stage, `0` for knockout |
| `host_diff` | host-advantage difference in `{-1, 0, 1}` |
| `team_a_confederation_idx` | fixed confederation index for team A |
| `team_b_confederation_idx` | fixed confederation index for team B |
| `z_log_top_15_average_value_team_a` | tournament-relative squad value z-score for team A |
| `z_log_top_15_average_value_team_b` | tournament-relative squad value z-score for team B |

Target labels come from de-vigged bookmaker consensus probabilities in `matched_odds.json`. Each bookmaker 1X2 triple is first converted into fairer implied probabilities by removing the overround, then the stage takes the component-wise median across bookmakers for home, draw, and away, and finally renormalizes that median triple so it sums to 1.0.

`baseline__market_dispersion` uses the bookmaker triple with the largest average absolute gap from that median target. It is included as a market-disagreement reference: the point is to show that even before any model is fit, the market itself does not offer one single exact pre-match probability vector.

## Layout

```text
Match_model/
|-- main_cli.py
|-- requirements.txt
|-- README.md
|-- results.md
|-- scripts/
|-- src/match_model/
|-- tests/
`-- data/
    |-- input/legacy12/
    |-- reference/old_stats/
    `-- output/
```

## Setup

Requires Python 3.10+.

From the `WorldCup2026 Bracket` repo root:

```powershell
cd Match_model
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Refresh inputs

```powershell
.\scripts\sync_inputs.ps1
```

This refreshes the committed `legacy12` collection inputs from `..\Data_Collection\data\legacy12`.
It copies `fixtures_stats.json`, `matched_odds.json`, `team_confederations.json`, `team_ratings.json`, and `tournament_squads_with_value.json` into this stage's `data/input/legacy12/`.

The helper script above is written for PowerShell on Windows. On macOS or Linux, skip the script and run the Python CLI commands in this stage directly after copying or syncing the required inputs.

## Commands

```powershell
python main_cli.py build-dataset
python main_cli.py run-loto
python main_cli.py run-all
python main_cli.py match-vs-market
```

`match-vs-market` scores LOTO CatBoost predictions against 90-minute actual results from `data/reference/old_stats/` and writes `data/output/experiments/match_vs_market_report.md`. Section 6 of `results.md` summarizes the same analysis; regenerate that report after changing predictions or the `old_stats` reference tree.

Explicit WC2026 holdout:

```powershell
python main_cli.py build-dataset --collection-dir data/input/legacy12 --old-stats-dir data/reference/old_stats --output data/output/datasets/match_dataset.json
python main_cli.py build-dataset --collection-dir ..\Data_Collection\data\wc2026 --old-stats-dir data/reference/old_stats --output data/output/datasets/wc2026_match_dataset.json
python main_cli.py run-holdout --train-dataset data/output/datasets/match_dataset.json --test-dataset data/output/datasets/wc2026_match_dataset.json --held-out-competition "World Cup 2026"
```

Default locations:

| Flag | Default |
|------|---------|
| `--collection-dir` | `data/input/legacy12` |
| `--old-stats-dir` | `data/reference/old_stats` |
| `--output` | `data/output/datasets/match_dataset.json` |
| `--output-dir` | `data/output/experiments` |
| `--seed` | `42` |

## Outputs

Key committed outputs from historical LOTO:

| Artifact | Meaning |
|------|---------|
| `data/output/datasets/match_dataset.json` | modeling dataset |
| `data/output/datasets/match_dataset_summary.json` | dataset summary |
| `data/output/experiments/loto_eval_results.json` | experiment summaries |
| `data/output/experiments/loto_eval_leaderboard.csv` | leaderboard |
| `data/output/experiments/loto_eval_per_fold.csv` | per-fold metrics |
| `data/output/experiments/loto_eval_predictions.csv` | per-match historical LOTO predictions |
| `data/output/experiments/plots/` | committed diagnostic plots |
| `data/output/experiments/match_vs_market_report.md` | match-level model vs market vs actual outcomes |
| `results.md` | narrative report tied to the committed outputs |

Committed outputs from the explicit WC2026 holdout:

| Artifact | Meaning |
|------|---------|
| `data/output/datasets/wc2026_match_dataset.json` | WC2026 test dataset built from the current tournament inputs |
| `data/output/experiments/wc2026_holdout_eval_results.json` | explicit holdout experiment summaries |
| `data/output/experiments/wc2026_holdout_eval_leaderboard.csv` | explicit holdout leaderboard |
| `data/output/experiments/wc2026_holdout_eval_per_fold.csv` | per-experiment holdout metrics |
| `data/output/experiments/wc2026_holdout_eval_predictions.csv` | per-match holdout predictions |

## Tests

```powershell
python -m unittest discover -s tests -v
```

The committed tests are smoke-level checks for path stability and report generation. They are not a full model-validation suite.

## Notes

- `old_stats` is vendored in `data/reference/old_stats`, so this stage does not depend on any folder outside `WorldCup2026 Bracket`.
- Match-level actual outcomes are joined from the vendored `old_stats` text files on `(tournament_id, date, team pair)`. If a collection input date disagrees with `old_stats`, the match is dropped from the `match-vs-market` report; Euro 2016 Group E round-three fixtures (Belgium–Sweden, Ireland–Italy) were corrected from Jun 21 to Jun 22 in `euro-master/2016--france/euro.txt` to match the committed inputs.
- `results.md` is generated from the committed experiment outputs and should be regenerated if those outputs change.
- Reproduction instructions assume the repo root is `WorldCup2026 Bracket`.
- The evaluation target is the de-vigged market consensus, so the target-oracle row is a sanity check for label handling, not a real forecasting benchmark.
- `baseline__market_dispersion` is useful as a reference because it reads market structure directly; the fairer predictive comparison is CatBoost versus `baseline__elo`.
- The explicit WC2026 holdout reuses models trained on legacy12 and is reported alongside, but separate from, the historical LOTO folds.
- The committed tests are smoke-level checks for paths and report generation; they do not replace deeper model-validation work.
