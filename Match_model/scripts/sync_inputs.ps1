# Copy collection data into this standalone stage (run after Data_Collection updates).
# The old_stats reference tree is vendored in this repo and updated in place when needed.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$LegacySrc = Join-Path $Root "..\Data_Collection\data\legacy12"
$LegacyDst = Join-Path $Root "data\input\legacy12"

New-Item -ItemType Directory -Force -Path $LegacyDst | Out-Null
Copy-Item (Join-Path $LegacySrc "fixtures_stats.json") -Destination $LegacyDst -Force
Copy-Item (Join-Path $LegacySrc "matched_odds.json") -Destination $LegacyDst -Force
Copy-Item (Join-Path $LegacySrc "teams_ratings.json") -Destination (Join-Path $LegacyDst "team_ratings.json") -Force
Copy-Item (Join-Path $LegacySrc "team_confederations.json") -Destination $LegacyDst -Force
Copy-Item (Join-Path $LegacySrc "tournament_squads_with_value.json") -Destination $LegacyDst -Force

Write-Host "Synced legacy12 inputs -> $LegacyDst"
Write-Host "old_stats reference remains vendored under data\\reference\\old_stats"
