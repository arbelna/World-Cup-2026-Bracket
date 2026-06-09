$ErrorActionPreference = "Stop"
$StageRoot = Split-Path -Parent $PSScriptRoot
$MatchModel = Join-Path (Split-Path -Parent $StageRoot) "Match_model"
$DataCollection = Join-Path (Split-Path -Parent $StageRoot) "Data_Collection"
$InputDir = Join-Path $StageRoot "data\input"

New-Item -ItemType Directory -Force -Path $InputDir | Out-Null

Copy-Item -Force (Join-Path $MatchModel "data\output\datasets\match_dataset.json") (Join-Path $InputDir "match_dataset.json")
if (Test-Path (Join-Path $MatchModel "data\output\datasets\wc2026_match_dataset.json")) {
  Copy-Item -Force (Join-Path $MatchModel "data\output\datasets\wc2026_match_dataset.json") (Join-Path $InputDir "wc2026_match_dataset.json")
}
Copy-Item -Force (Join-Path $DataCollection "data\legacy12\fixtures_stats.json") (Join-Path $InputDir "fixtures_stats.json")
Copy-Item -Force (Join-Path $DataCollection "data\legacy12\teams_ratings.json") (Join-Path $InputDir "team_ratings.json")
Copy-Item -Force (Join-Path $DataCollection "data\wc2026\fixtures_stats.json") (Join-Path $InputDir "wc2026_fixtures_stats.json")
Copy-Item -Force (Join-Path $DataCollection "data\wc2026\teams_ratings.json") (Join-Path $InputDir "wc2026_team_ratings.json")
Copy-Item -Force (Join-Path $DataCollection "data\wc2026\tournament_squads_with_value.json") (Join-Path $InputDir "wc2026_tournament_squads_with_value.json")
if (Test-Path (Join-Path $DataCollection "data\wc2026\matched_odds.json")) {
  Copy-Item -Force (Join-Path $DataCollection "data\wc2026\matched_odds.json") (Join-Path $InputDir "wc2026_matched_odds.json")
}

$OldStatsSrc = Join-Path $MatchModel "data\reference\old_stats\worldcup-master"
$OldStatsDest = Join-Path $InputDir "old_stats\worldcup-master"
New-Item -ItemType Directory -Force -Path $OldStatsDest | Out-Null
Copy-Item -Recurse -Force (Join-Path $OldStatsSrc "*") $OldStatsDest

Write-Host "Synced inputs to $InputDir"
