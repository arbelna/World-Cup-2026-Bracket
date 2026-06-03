# WorldCup2026 Bracket - Data_Collection

Collection stage for the inputs consumed later by `Match_model` and `Bracket_Simulations`.

## Scope

- This stage builds the historical and current-tournament inputs consumed later by `Match_model` and `Bracket_Simulations`.
- Elo fixtures/results provide the canonical match list and pre-match rating signals; OddsPortal prices provide bookmaker-implied 1X2 probabilities used later as both labels and market references; Wikipedia squads and Transfermarkt values provide the squad-strength features that become normalized market-value inputs in the match model.
- Sources:
  - Elo fixtures/results and ratings
  - confederations
  - OddsPortal 1X2 odds
  - Wikipedia squads
  - Transfermarkt market values via DuckDB first, then API fallback
- Partitions:
  - `legacy12`: the 12 completed tournaments used for training, evaluation, and historical bracket backtesting
  - `wc2026`: the current World Cup 2026 collection used for forward-looking holdout and simulation inputs
- Code lives entirely in this directory under `src/data_collection/`.

The `legacy12` partition contains these historical tournaments: Euro 2012, Euro 2016, Euro 2020, Euro 2024, World Cup 2010, World Cup 2014, World Cup 2018, World Cup 2022, Copa America 2016, Copa America 2019, Copa America 2021, and Copa America 2024.

## Current committed status

Snapshot taken from committed manifests:

### `legacy12`

| Stage | Status | Counts |
|------|--------|--------|
| Elo | complete | 558 fixtures, 270 team ratings |
| Confederations | complete | 222 teams mapped |
| OddsPortal | complete | 3,384 raw rows, 3,382 matched, 0 unmatched, 2 invalid dropped |
| Transfermarkt | complete | 6,538 players, 6,418 valued, 120 unmatched |

Last completed stage in the committed manifest: `resolve_transfermarkt_from_existing` on `2026-05-31`.

### `wc2026`

| Stage | Status | Counts |
|------|--------|--------|
| Elo | complete | 72 fixtures, 48 team ratings |
| Confederations | complete | 222 teams mapped |
| OddsPortal | complete | 724 raw rows, 724 matched, 0 unmatched |
| Transfermarkt | complete | 1,247 players, 1,236 valued, 11 unmatched |

## Layout

```text
Data_Collection/
|-- main_cli.py
|-- requirements.txt
|-- README.md
|-- scripts/
|-- src/data_collection/
|-- tests/
`-- data/
    |-- legacy12/
    `-- wc2026/
```

## Setup

Requires Python 3.10+.

From the `WorldCup2026 Bracket` repo root:

```powershell
cd Data_Collection
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python main_cli.py --partition legacy12 update-tm-db
```

The local DuckDB snapshot is intentionally gitignored.

The helper command examples in this README use PowerShell on Windows. On macOS or Linux, run the same `python main_cli.py ...` commands directly from this stage directory.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Main commands

### Elo and confederations

```powershell
python main_cli.py --partition legacy12 collect-elo
python main_cli.py --partition legacy12 collect-confederations
python main_cli.py --partition wc2026 collect-elo
python main_cli.py --partition wc2026 collect-confederations
```

### OddsPortal

```powershell
python main_cli.py --partition legacy12 collect-odds-all --odds-workers 2
python main_cli.py --partition legacy12 match-odds
python main_cli.py --partition legacy12 generate-missing-template
```

- `match-odds`: join scraped OddsPortal rows to the canonical fixture ids from `fixtures_stats.json`.
- `generate-missing-template`: write a local template for unresolved odds rows that need manual help before a second collection pass.

If `missing_odds_manual.json` is filled locally:

```powershell
python main_cli.py --partition legacy12 collect-odds-missing --odds-workers 2
```

### Transfermarkt

```powershell
python main_cli.py --partition legacy12 collect-transfermarkt
python main_cli.py --partition legacy12 resolve-transfermarkt-existing
python main_cli.py --partition legacy12 update-tm-db --force
```

The default committed workflow expects the local DuckDB file at:

`data/transfermarkt-datasets.duckdb`

It is not committed to Git.

### Manifest repair

```powershell
python main_cli.py --partition legacy12 sync-manifest
python main_cli.py --partition wc2026 sync-manifest
```

Manifest counts are derived from on-disk outputs, so `sync-manifest` is safe after manual cleanup.

## Pulling WC2026 data

The current committed `wc2026` snapshot already includes Elo fixtures, Elo ratings, team confederations, matched OddsPortal prices, and Transfermarkt-enriched squad outputs. Re-running the steps below is mainly useful when you want to refresh the snapshot or collect newer market and squad data.

Recommended command order:

1. Collect Elo fixtures and ratings:

```powershell
python main_cli.py --partition wc2026 collect-elo
```

2. Collect confederations:

```powershell
python main_cli.py --partition wc2026 collect-confederations
```

3. Refresh OddsPortal collection and fixture matching:

```powershell
python main_cli.py --partition wc2026 collect-odds-all --odds-workers 2
python main_cli.py --partition wc2026 match-odds
```

4. Refresh Transfermarkt-enriched squad data:

```powershell
python main_cli.py --partition wc2026 collect-transfermarkt
```

5. Recompute the manifest after any of the steps above:

```powershell
python main_cli.py --partition wc2026 sync-manifest
```

Current expected committed outputs under `data/wc2026/`:

- `fixtures_stats.json`
- `teams_ratings.json`
- `team_confederations.json`
- `oddsportal_raw_odds.json`
- `matched_odds.json`
- `unmatched_odds.json`
- `tournament_squads.json`
- `tournament_squads_with_value.json`
- `tournament_squads_unmatched_players.json`
- `manifest.json`

## Output files

Each partition may contain:

| File | Meaning |
|------|---------|
| `fixtures_stats.json` | Elo fixtures/results |
| `teams_ratings.json` | Elo ratings snapshot |
| `team_confederations.json` | team -> confederation map |
| `oddsportal_raw_odds.json` | raw scraped odds rows |
| `matched_odds.json` | odds matched to fixture ids |
| `unmatched_odds.json` | odds that could not be matched |
| `tournament_squads.json` | raw Wikipedia squads |
| `tournament_squads_with_value.json` | squads with market values attached |
| `tournament_squads_unmatched_players.json` | unresolved players |
| `manifest.json` | timestamps and counts |

Local-only workflow files such as `missing_odds_manual.json`, `transfermarkt_manual_links.json`, and the DuckDB snapshot are intentionally gitignored.

## Notes

- Committed manifests should stay machine-neutral. They should not contain absolute local filesystem paths.
- This stage is the only network-heavy part of the repository.
- The committed JSON outputs are intended as reproducible inputs for later stages, not as a claim that live collection can run indefinitely without source-site changes.
