Vendored historical tournament text sources used to recover stage labels and actual match results.

## Purpose

`Match_model` uses these files to attach competition-stage metadata such as `group`, `R16`, `QF`, `SF`, `third_place`, and `final` to the historical Elo fixtures. They are also the source used to recover actual 90-minute results when the report compares model and market calls against what happened on the pitch.

## How they are used

- Parser entrypoint: `src/match_model/parsers/old_stats_parser.py`
- Dataset build: `src/match_model/dataset_builder.py`
- Report actual-outcome lookup: `src/match_model/results_report.py`

The parser extracts:

- tournament id
- match date
- teams
- stage
- 90-minute score
- extra-time score when present
- penalty winner when present
- advancing team for knockout matches

## Why they are committed

- They are part of the dataset construction contract for `Match_model`.
- They keep stage labeling reproducible even if the original upstream folder structure is no longer available elsewhere.
- They let the published evaluation report explain prediction errors using the real historical outcomes.
