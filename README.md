![FIFA World Cup 2026 Official Brand unveiled in Los Angeles](./Data_Collection/FIFA-World-Cup-26-Official-Brand-unveiled-in-Los-Angeles.png)

# WorldCup2026 Bracket

`WorldCup2026 Bracket` is a three-stage pipeline for collecting international tournament data, training a match-level 1X2 probability model, and backtesting full tournament bracket simulations.

The project asks whether a small set of public pre-match signals can recover bookmaker-style match probabilities and still remain useful once those probabilities are pushed through full tournament brackets. In practice, the repo tests how far Elo, squad market values, confederation membership, and de-vigged bookmaker consensus can take the pipeline from historical data collection to bracket-level backtests.

## Pipeline

1. `Data_Collection`
   Collects and normalizes historical inputs such as Elo fixtures, bookmaker odds, squad lists, and squad market values.
2. `Match_model`
   Builds the historical match dataset and runs leave-one-tournament-out evaluation for the CatBoost match model and baseline methods.
3. `Bracket_Simulations`
   Simulates full World Cup brackets under market-derived and model-derived probabilities, then evaluates stage-level predictions against the historical outcomes.

## Repository layout

- `Data_Collection/`: collectors, manifests, tests, and committed partition outputs.
- `Match_model/`: dataset build, model evaluation, committed experiment outputs, and report.
- `Bracket_Simulations/`: simulation engine, committed backtest summaries, and compare outputs.

## Curated committed outputs

- `Match_model/results.md` (includes section 6: explicit WC2026 holdout evaluation)
- `Match_model/data/output/experiments/plots/`
- `Bracket_Simulations/results.md`
- `Bracket_Simulations/data/output/simulations/stage_prediction_backtest.md`
- `Bracket_Simulations/data/output/compare_summary.json`
- `Bracket_Simulations/data/output/compare_brier_summary.md`

The repository keeps curated summaries and the inputs needed to understand them. It does not keep every local rerun artifact.

## Not committed

- `.git/` (local history only; never part of the published tree)
- Virtual environments, Python caches, editor folders (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.vscode/`, `catboost_info/`, `*.pyc`)
- Temporary files (`*.log`, `*.tmp`, `_tmp_*`)
- `Data_Collection/data/transfermarkt-datasets.duckdb`
- `Data_Collection/data/**/missing_odds_manual.json` and `transfermarkt_manual_links.json`
- `docs_audit.md`
- JSON under `Bracket_Simulations/data/output/simulations/` (run logs, settings, state, etc.)
- Under each `.../simulations/wc*/market_all/<fingerprint>/` and `.../model_all/<fingerprint>/`: everything except `stage_config_probabilities.csv` and `team_stage_probabilities.csv`
- `.github/`, `.editorconfig`, `.gitattributes`, and `.gitignore` files (local-only)

Committed data includes all `data/**/input` and `data/**/output` JSON and CSV elsewhere; under `Bracket_Simulations/data/output/simulations/` only curated Markdown at the folder root (e.g. `stage_prediction_backtest.md`) plus those two CSVs per fingerprint, plus `Data_Collection/FIFA-World-Cup-26-Official-Brand-unveiled-in-Los-Angeles.png`.

## Quick start

Requires Python 3.10+.

The PowerShell commands below are convenience examples for Windows. On macOS or Linux, use the same Python commands directly from each stage directory.

Before running the commands below, set up each stage once from its own directory with `python -m venv .venv` and `pip install -r requirements.txt`.

From the repo root:

```powershell
cd Data_Collection
python -m unittest discover -s tests -v

cd ..\Match_model
python -m unittest discover -s tests -v
python main_cli.py run-all

cd ..\Bracket_Simulations
python -m pytest tests -q
python main_cli.py run-all
```

## Sources and references

- World Football Elo Ratings: https://eloratings.net/
- OddsPortal football odds archive: https://www.oddsportal.com/football/
- Wikipedia tournament squad pages: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads
- Transfermarkt: https://www.transfermarkt.com/

These are the main external data sources behind the committed inputs. Stage-level READMEs describe how each source is used inside the pipeline.

## License

This repository is released under the MIT License. See [LICENSE](LICENSE).
