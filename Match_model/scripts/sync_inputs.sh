#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LEGACY_SRC="$ROOT/../Data_Collection/data/legacy12"
LEGACY_DST="$ROOT/data/input/legacy12"

mkdir -p "$LEGACY_DST"
cp "$LEGACY_SRC/fixtures_stats.json" "$LEGACY_DST/"
cp "$LEGACY_SRC/matched_odds.json" "$LEGACY_DST/"
cp "$LEGACY_SRC/teams_ratings.json" "$LEGACY_DST/team_ratings.json"
cp "$LEGACY_SRC/team_confederations.json" "$LEGACY_DST/"
cp "$LEGACY_SRC/tournament_squads_with_value.json" "$LEGACY_DST/"

printf '%s\n' "Synced legacy12 inputs -> $LEGACY_DST"
printf '%s\n' "old_stats reference remains vendored under data/reference/old_stats"
