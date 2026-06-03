# Historical WCs 2010-2022: market_all + model_all @ 200k, then analysis + backtest reports.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONPATH = "src"

$targetSims = 200000
$batchSize = 1000
$seed = 42

$tournaments = @("wc2010", "wc2014", "wc2018", "wc2022")
$modes = @("market_all", "model_all")

Write-Host "=== Write actual participants ===" -ForegroundColor Cyan
python -m bracket_simulations.prediction_backtest write-actuals
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($t in $tournaments) {
    foreach ($m in $modes) {
        Write-Host "=== $t $m - fresh $targetSims sims ===" -ForegroundColor Cyan
        python main_cli.py simulate --tournament $t --mode $m --n-sims $targetSims --batch-size $batchSize --seed $seed --reset -v
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "=== Analyze all bracket outputs ===" -ForegroundColor Cyan
python -m bracket_simulations.prediction_backtest analyze
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Stage prediction backtest reports ===" -ForegroundColor Cyan
python -m bracket_simulations.prediction_backtest backtest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done." -ForegroundColor Green
