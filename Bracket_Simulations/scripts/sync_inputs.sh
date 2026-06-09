#!/usr/bin/env sh
set -eu

STAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MATCH_MODEL="$STAGE_ROOT/../Match_model"
DATA_COLLECTION="$STAGE_ROOT/../Data_Collection"
INPUT_DIR="$STAGE_ROOT/data/input"

mkdir -p "$INPUT_DIR"

cp "$MATCH_MODEL/data/output/datasets/match_dataset.json" "$INPUT_DIR/match_dataset.json"
if [ -f "$MATCH_MODEL/data/output/datasets/wc2026_match_dataset.json" ]; then
  cp "$MATCH_MODEL/data/output/datasets/wc2026_match_dataset.json" "$INPUT_DIR/wc2026_match_dataset.json"
fi
cp "$DATA_COLLECTION/data/legacy12/fixtures_stats.json" "$INPUT_DIR/fixtures_stats.json"
cp "$DATA_COLLECTION/data/legacy12/teams_ratings.json" "$INPUT_DIR/team_ratings.json"
cp "$DATA_COLLECTION/data/wc2026/fixtures_stats.json" "$INPUT_DIR/wc2026_fixtures_stats.json"
cp "$DATA_COLLECTION/data/wc2026/teams_ratings.json" "$INPUT_DIR/wc2026_team_ratings.json"
cp "$DATA_COLLECTION/data/wc2026/tournament_squads_with_value.json" "$INPUT_DIR/wc2026_tournament_squads_with_value.json"
if [ -f "$DATA_COLLECTION/data/wc2026/matched_odds.json" ]; then
  cp "$DATA_COLLECTION/data/wc2026/matched_odds.json" "$INPUT_DIR/wc2026_matched_odds.json"
fi

mkdir -p "$INPUT_DIR/old_stats/worldcup-master"
cp -R "$MATCH_MODEL/data/reference/old_stats/worldcup-master/." "$INPUT_DIR/old_stats/worldcup-master/"

printf '%s\n' "Synced inputs to $INPUT_DIR"
