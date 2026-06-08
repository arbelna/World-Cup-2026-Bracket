# WorldCup2026 Bracket - Bracket_Simulations

Stage 3 of the local pipeline: backtest historical World Cup brackets for 2010-2022 and run forward bracket simulations for WC2026 from the same committed upstream inputs.

## Scope

- Historical tournaments (`wc2010`, `wc2014`, `wc2018`, `wc2022`) are simulated against known outcomes so the stage can backtest stage predictions. Future tournaments such as `wc2026` are simulated forward-only: they produce bracket probabilities, but there are no actual results yet to score against.
- Simulate the same tournament structure under two probability modes:
  - `market_all`: bookmaker-derived probabilities, using historical market prices directly whenever they exist
  - `model_all`: CatBoost pairwise probabilities from `Match_model`
- Produce:
  - marginal reach probabilities by stage
  - exact stage-configuration distributions
  - compare summaries
  - stage-prediction backtest reports

This stage depends only on sibling folders inside `WorldCup2026 Bracket`.

## Prerequisites

1. `Match_model` has already produced the committed dataset and experiment outputs.
2. Required inputs have been synced into `Bracket_Simulations/data/input`.

## Layout

```text
Bracket_Simulations/
|-- main_cli.py
|-- README.md
|-- results.md
|-- config/
|-- scripts/
|-- src/bracket_simulations/
|-- tests/
`-- data/
    |-- input/
    `-- output/
```

## Setup

Requires Python 3.10+.

From the `WorldCup2026 Bracket` repo root:

```powershell
cd Bracket_Simulations
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Commands

Typical order:

1. `sync-inputs` - copy the committed match-model outputs needed by this stage.
2. `build-data` - build the tournament input files and bracket structures from config.
3. `precompute-pairs` - compute pairwise match probabilities for one tournament at a time.
4. `simulate` - run Monte Carlo simulations for a chosen tournament and probability mode.
5. `backtest report` or `backtest run-historical` - write the human-facing summary and the detailed historical backtest report.
6. `compare` - write the market-vs-model comparison summaries.

```powershell
python main_cli.py sync-inputs
python main_cli.py build-data
python main_cli.py precompute-pairs --tournament wc2022
python main_cli.py simulate --tournament wc2022 --mode model_all --n-sims 200000 --reset -v
python main_cli.py backtest report
python main_cli.py compare
```

The `wc2022` `precompute-pairs` example above is a pattern. Run the same command per tournament (`wc2010`, `wc2014`, `wc2018`, `wc2022`, and any configured future tournament such as `wc2026`) before simulating that tournament.

The helper script examples in this stage are written for PowerShell on Windows. On macOS or Linux, run the same `python main_cli.py ...` commands directly from this directory.

`python main_cli.py compare` writes:

- `data/output/compare_summary.json`
- `data/output/compare_brier_summary.md`

The historical backtest report is written to:

- `results.md`
- `data/output/simulations/stage_prediction_backtest.md`

## Simulation behavior

### Group stage

- Round-robin fixtures are sampled from 1X2 probabilities.
- Group standings are driven by points.
- Ties on points are broken probabilistically using pairwise strengths derived from the relevant match probabilities.
- For WC2026 best third-place qualification, the simulator does not use FIFA goal-difference rules because it tracks only 1X2 outcomes rather than exact scores. When third-place teams are tied on points, it falls back to pairwise-strength ranking.

### Knockout stage

- First sample the 90-minute result.
- If the match is drawn after 90 minutes, advance one side using the configured knockout tie-break logic for that mode.

### Probability sources

- In `market_all`, direct market 1X2 odds are used whenever the pairing already exists in the historical market data.
- If a knockout pairing is missing from the direct market set, the stage fits a Davidson model on the tournament's market soft labels and uses that model to supply the missing 90-minute probabilities.
- In `model_all`, both the group stage and the knockout stage use the committed pairwise predictions produced upstream by `Match_model`.
- Historical backtests use pre-match Elo inside the upstream match-model pipeline. WC2026 forward simulation uses the pre-tournament Elo snapshot for every pairing because no played-match Elo updates exist yet.

### Bradley-Terry and Davidson

- Bradley-Terry is a pairwise strength model with no explicit draw state: stronger teams get higher win probabilities in head-to-head comparisons.
- Davidson extends Bradley-Terry by adding a draw parameter, which makes it suitable for football 1X2 probabilities.
- In this repo, the Davidson fit is only used to fill missing knockout market pairings; it does not replace direct market prices when those prices already exist.

### Tie-break weighting and alpha

- Group-stage tie breaks use pairwise strengths averaged across the teams tied on points.
- For a tied cluster, each pairwise edge is transformed as `p_ij^alpha / (p_ij^alpha + p_ji^alpha)`, then averaged across opponents, where `p_ij` is the probability of team `i` beating team `j` in a 90-minute match.
- Knockout draws are resolved with the related softened win weight `p_a^alpha / (p_a^alpha + p_b^alpha)` after the 90-minute draw has been sampled.
- `alpha` controls how sharp the tie-break preference is:
  - lower `alpha` flattens the edge and makes tie breaks more random
  - higher `alpha` sharpens the edge and makes the stronger side more likely to advance
- Current defaults in the committed configs:
  - `group_tie = 1.0`
  - `R16 = QF = SF = third_place = final = 0.5`

### Simplifications relative to real FIFA rules

The simulator tracks only 1X2 outcomes (win / draw / loss) and not exact scores. This makes two real-world procedures impossible to implement faithfully:

**Group stage tiebreaks.** The real FIFA procedure for teams equal on points is: (1) goal difference, (2) goals scored, (3) head-to-head points, (4) head-to-head goal difference, (5) head-to-head goals scored, (6) drawing of lots. Because the simulator has no score data, it replaces all of these with a pairwise-strength ranking: each tied team's strength edge against every other tied team is computed from the match probabilities, then averaged. This is a reasonable proxy for relative quality but does not reproduce the exact FIFA rule. The effect is most visible in WC2026, where the best-third-place qualification rule depends on group performance across all groups simultaneously.

**Knockout draws (extra time and penalties).** When the 90-minute result is a draw, the real procedure is 30 minutes of extra time followed by a penalty shootout if still level. The simulator skips extra time entirely and resolves the draw immediately using `p_a^alpha / (p_a^alpha + p_b^alpha)`, a softened version of the teams' relative 90-minute win probabilities. At the default `alpha = 0.5` the resolution is close to a coin flip that favours the stronger side slightly. This is a known simplification: it means the simulator does not model the distinct dynamics of penalty shootouts or the fatigue effects of extra time. For the purpose of bracket-level probability estimation over many simulations, the aggregate effect is small, but individual upset paths that depend on penalty outcomes are not captured.

## Committed outputs

The repo intentionally keeps only curated summary outputs at the root level of this stage:

| Artifact | Meaning |
|------|---------|
| `results.md` | curated human-facing historical backtest summary |
| `data/output/simulations/stage_prediction_backtest.md` | fuller generated historical backtest report in the output location |
| `data/output/simulations/stage_prediction_backtest.json` | machine-readable backtest summary |
| `data/output/compare_summary.json` | compare output from `main_cli.py compare` |
| `data/output/compare_brier_summary.md` | compare markdown summary |

Per-fingerprint run folders under `data/output/simulations/wc*/{market_all,model_all}/<hash>/`, including WC2026 forward-simulation outputs, are local run artifacts rather than part of the curated root-level summary set.

## Tests

```powershell
python -m pytest tests -q
```

These tests assume the committed inputs are present. They validate stage sizes, actual results, and basic provider wiring.

## Dashboard

An interactive HTML dashboard is available at `docs/index.html` and published via GitHub Pages.

### Generating the data files

After running simulations for `wc2026` in both modes, export the dashboard data:

```powershell
cd Bracket_Simulations
python scripts/export_dashboard_json.py
```

This writes `docs/data/market.json`, `docs/data/model.json`,
`docs/data/market_sim_matrix.npz`, and `docs/data/model_sim_matrix.npz`.
