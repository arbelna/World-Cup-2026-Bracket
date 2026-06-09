Bundled historical collection inputs for `Match_model`.

## Purpose

This directory is the committed handoff from `Data_Collection` into the match-model stage. It lets `Match_model` rebuild the dataset and regenerate the published evaluation outputs without re-running the collection pipeline.

## Provenance

- Source stage: sibling folder `..\..\..\Data_Collection`
- Sync script: `Match_model/scripts/sync_inputs.ps1`
- Source partition: `Data_Collection/data/legacy12`

The sync script copies the files from the sibling `Data_Collection` stage into this directory so `Match_model` stays self-contained inside `WorldCup2026 Bracket`.

## Required committed files

- `fixtures_stats.json`: normalized historical fixtures and match metadata; rows are matched back to the tournament-start rating snapshots during dataset construction
- `matched_odds.json`: fixture-level bookmaker odds already matched to the historical fixtures
- `team_ratings.json`: tournament-start Elo snapshots used as the rating source of truth for `elo_diff`
- `team_confederations.json`: national-team to confederation mapping
- `tournament_squads_with_value.json`: tournament squads with attached market values

## Why these files are committed

- They are the exact historical inputs used to build `match_dataset.json`.
- They make the published `results.md` reproducible without network access.
- They keep the interface between `Data_Collection` and `Match_model` explicit and inspectable.
