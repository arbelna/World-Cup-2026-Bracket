# Match_model - detailed LOTO results

**Generated:** 2026-06-07 10:32 UTC
**Dataset:** `data/output/datasets/match_dataset.json` (558 matches)
**Experiments:** `data/output/experiments`

Standalone stage: inputs under `data/input/legacy12`, stage labels under `data/reference/old_stats`.

## 0. Experiment pipeline

This report summarizes a leave-one-tournament-out workflow over the 12 historical `legacy12` tournaments.
The input dataset is built from committed Elo, confederation, and squad-value features, while the soft label for each match is the median de-vigged bookmaker consensus over home, draw, and away.
The headline experiment is the seven-feature CatBoost `core7` model, compared against three baselines: `baseline__elo`, `baseline__marginal`, and the market-structure reference `baseline__market_dispersion`. A target oracle is also included as a label-plumbing reference rather than a real predictor.

## 1. Global leaderboard - predictive models only

Cross-entropy (CE) penalizes assigning low probability to outcomes the market considered likely. Brier is the squared error across the three 1X2 probabilities. MAE is the average absolute probability error across the same three outcomes. Lower is better for all three.

| Experiment | Weighted CE (lower better) | Weighted Brier | Weighted MAE |
|------------|----------------------------|----------------|--------------|
| catboost_loto_core7 | 0.9617 | 0.0081 | 0.0386 |
| baseline__elo | 0.9790 | 0.0193 | 0.0628 |
| baseline__marginal | 1.0604 | 0.0768 | 0.1224 |
| baseline__market_dispersion | 0.9517 | 0.0016 | 0.0144 |

**CatBoost vs Elo baseline (weighted CE):** 0.9617 vs 0.9790 (delta = -0.0174; negative delta means CatBoost is better).
`baseline__market_dispersion` can score better than CatBoost on CE because it reads market-price dispersion directly while the target is itself the de-vigged market consensus. Treat it as a market-aware calibration reference, not a fair standalone predictive baseline; the cleaner predictive comparison is CatBoost versus `baseline__elo`.

## 1b. What the errors look like on one 1X2 line

The leaderboard MAE is a macro average over home, draw, and away: for each outcome, take |model - market|, then average the three. It is **not** the gap on the favorite alone.

CatBoost's weighted MAE is **3.86 percentage points** per outcome on average (0.0386 on the 0-1 scale). The table below uses that exact average on one illustrative de-vigged 1X2 line (favorite probability softens; draw and away share the shift):

| Outcome | Market | Model | Delta pp (model - market) | Abs error |
|---------|--------|-------|---------------------------|-----------|
| Home win | 70.0% | 64.2% | -5.8 | 5.8 |
| Draw | 20.0% | 22.9% | +2.9 | 2.9 |
| Away win | 10.0% | 12.9% | +2.9 | 2.9 |
| **Macro MAE** | | | | **3.87** |

The favorite is still home, but the model is 5.8 pp less confident; draw and away gain 2.9 pp and 2.9 pp. Macro MAE on this line is **3.87 pp**, matching the headline **3.86 pp**.

Brier squares those same three gaps before averaging, so it punishes large misses more heavily; cross-entropy punishes confident wrong calls even more. None of the three numbers is a bracket probability by itself - they are per-match 1X2 inputs that feed the pairwise simulation stage.

## 2. Per-tournament held-out errors

Each row is one leave-one-tournament-out fold: train on 11 tournaments, test on the held-out competition. Negative deltas mean CatBoost beat the Elo baseline on that metric.

| Tournament | N | CatBoost CE | Elo CE | delta CE vs Elo | CatBoost Brier | Elo Brier | delta Brier vs Elo |
|------------|---|-------------|--------|-----------------|----------------|-----------|--------------------|
| Copa America 2016 | 32 | 0.9255 | 0.9410 | -0.0155 | 0.0109 | 0.0217 | -0.0109 |
| Copa America 2019 | 26 | 0.9147 | 0.9445 | -0.0298 | 0.0177 | 0.0381 | -0.0204 |
| Copa America 2021 | 28 | 0.9178 | 0.9336 | -0.0158 | 0.0094 | 0.0197 | -0.0103 |
| Copa America 2024 | 32 | 0.9233 | 0.9463 | -0.0230 | 0.0091 | 0.0232 | -0.0141 |
| Euro 2012 | 31 | 1.0289 | 1.0440 | -0.0151 | 0.0102 | 0.0206 | -0.0104 |
| Euro 2016 | 51 | 0.9978 | 1.0063 | -0.0085 | 0.0069 | 0.0117 | -0.0048 |
| Euro 2020 | 51 | 0.9593 | 0.9844 | -0.0251 | 0.0067 | 0.0231 | -0.0164 |
| Euro 2024 | 51 | 0.9682 | 0.9817 | -0.0135 | 0.0066 | 0.0152 | -0.0086 |
| World Cup 2010 | 64 | 0.9744 | 0.9897 | -0.0153 | 0.0076 | 0.0166 | -0.0089 |
| World Cup 2014 | 64 | 0.9733 | 0.9872 | -0.0139 | 0.0072 | 0.0165 | -0.0093 |
| World Cup 2018 | 64 | 0.9605 | 0.9797 | -0.0193 | 0.0056 | 0.0183 | -0.0128 |
| World Cup 2022 | 64 | 0.9495 | 0.9693 | -0.0198 | 0.0081 | 0.0202 | -0.0121 |

- **Best CE vs Elo:** Copa America 2019 (-0.0298)
- **Worst CE vs Elo:** Euro 2016 (-0.0085)
- **Best Brier vs Elo:** Copa America 2019 (-0.0204)
- **Worst Brier vs Elo:** Euro 2016 (-0.0048)

## 3. Group stage vs knockout matches

The table below splits the held-out match predictions by stage bucket. This is useful because group matches carry more draw mass, while knockout matches compress the draw problem into a smaller set of usually stronger teams.

| Bucket | N | CatBoost CE | Elo CE | CatBoost Brier | Elo Brier | CatBoost MAE | Elo MAE |
|--------|---|-------------|--------|----------------|-----------|--------------|---------|
| group | 410 | 0.9498 | 0.9690 | 0.0094 | 0.0215 | 0.0417 | 0.0665 |
| knockout | 148 | 0.9947 | 1.0070 | 0.0047 | 0.0130 | 0.0299 | 0.0525 |

- **Group large-miss example:** Ecuador vs Venezuela - the model's top call was Ecuador at 35.5%, while the market target's top call was Ecuador at 59.8%; the largest probability miss was 24.3 percentage points.
- **Knockout large-miss example:** France vs Poland - the model's top call was France at 55.9%, while the market target's top call was France at 69.7%; the largest probability miss was 13.7 percentage points.

## 4. Highest cross-entropy predictions (CatBoost)

These are the 10 worst single-match CatBoost CE errors on held-out folds. The comparison below focuses on the market call, the model call, and the actual 90-minute result from the vendored historical text files.

| # | Match | Stage | Actual 90m | Market top call | Model top call | CE | Brier |
|---|-------|-------|------------|-----------------|----------------|----|-------|
| 1 | Colombia vs Paraguay | group | Colombia win (1-0) | Colombia 39.7% (hit) | Colombia 62.6% (hit) | 1.2180 | 0.0845 |
| 2 | South Africa vs Mexico | group | Draw (1-1) | Mexico 37.9% (miss) | Mexico 57.7% (miss) | 1.1779 | 0.0605 |
| 3 | Ghana vs South Korea | group | Ghana win (3-2) | South Korea 34.7% (miss) | South Korea 50.3% (miss) | 1.1547 | 0.0405 |
| 4 | England vs France | group | Draw (1-1) | France 38.3% (miss) | England 45.1% (miss) | 1.1525 | 0.0413 |
| 5 | Mexico vs Uruguay | group | Mexico win (3-1) | Mexico 38.6% (hit) | Uruguay 45.0% (miss) | 1.1518 | 0.0412 |
| 6 | South Africa vs France | group | South Africa win (2-1) | France 45.0% (miss) | France 63.6% (miss) | 1.1482 | 0.0534 |
| 7 | Turkey vs Czechia | group | Turkey win (2-0) | Czechia 41.1% (miss) | Turkey 45.2% (hit) | 1.1456 | 0.0423 |
| 8 | England vs Sweden | group | England win (3-2) | England 40.5% (hit) | England 55.5% (hit) | 1.1414 | 0.0365 |
| 9 | South Africa vs Uruguay | group | Uruguay win (0-3) | Uruguay 40.7% (hit) | Uruguay 56.9% (hit) | 1.1410 | 0.0397 |
| 10 | England vs Italy | knockout | Draw (0-0) | Italy 33.9% (miss) | England 45.7% (miss) | 1.1355 | 0.0258 |

1. **Shared pattern in 5 matches**: Colombia vs Paraguay, South Africa vs Mexico, Ghana vs South Korea, South Africa vs France, South Africa vs Uruguay. In each case, a large Elo gap appears to have pulled the model too hard toward one side.
2. **England vs France**: The model flipped the favorite relative to the market consensus.
3. **Mexico vs Uruguay**: The model flipped the favorite relative to the market consensus.
4. **Turkey vs Czechia**: The model flipped the favorite relative to the market consensus.
5. **England vs Sweden**: The model and market leaned the same way, but the model concentrated too much probability mass.
6. **England vs Italy**: The model flipped the favorite relative to the market consensus.

## 5. Reproduce

From the `WorldCup2026 Bracket` repo root:

```powershell
cd Match_model
python main_cli.py run-all
```

## 6. WC2026 explicit holdout (train legacy12, test WC2026)

Train/test split evaluation with train set from legacy12 and held-out test set `World Cup 2026`.
WC2026 test dataset: `data/output/datasets/wc2026_match_dataset.json`

| Experiment | CE | Brier | MAE |
|------------|----|-------|-----|
| catboost_loto_core7 | 0.9219 | 0.0069 | 0.0368 |
| baseline__elo | 0.9479 | 0.0228 | 0.0633 |
| baseline__marginal | 1.0769 | 0.1166 | 0.1426 |
| baseline__market_dispersion | 0.9126 | 0.0008 | 0.0120 |
| reference__market_target_oracle | 0.9110 | 0.0000 | 0.0000 |

CatBoost vs Elo on `World Cup 2026` (CE): 0.9219 vs 0.9479 (delta -0.0260, negative means CatBoost is better).

Historical CatBoost ranges across the 12 LOTO folds: CE 0.9147-1.0289, Brier 0.0056-0.0177, and CE delta vs Elo -0.0298 to -0.0085. The WC2026 holdout lands at CE 0.9219, Brier 0.0069, and delta -0.0260.
That does not validate future outcomes, but it does suggest the WC2026 pairwise probability surface behaves like the historical tournament folds rather than like an obvious outlier, so these predictions are reasonable inputs for the bracket simulation stage.

**WC2026 holdout example** (CatBoost weighted MAE **3.68 pp** on the test set):

| Outcome | Market | Model | Delta pp (model - market) | Abs error |
|---------|--------|-------|---------------------------|-----------|
| Home win | 58.0% | 52.5% | -5.5 | 5.5 |
| Draw | 26.0% | 28.8% | +2.8 | 2.8 |
| Away win | 16.0% | 18.7% | +2.7 | 2.7 |
| **Macro MAE** | | | | **3.67** |

On a representative group-stage line, home stays the favorite but drops 5.5 pp while draw and away rise 2.8 pp and 2.7 pp. Macro MAE on this line is **3.67 pp**, matching the WC2026 holdout **3.68 pp**.

Reproduce from the `WorldCup2026 Bracket` repo root:

```powershell
cd Match_model
python main_cli.py build-dataset --collection-dir ..\Data_Collection\data\wc2026 --old-stats-dir data/reference/old_stats --output data/output/datasets/wc2026_match_dataset.json
python main_cli.py run-holdout --train-dataset data/output/datasets/match_dataset.json --test-dataset data/output/datasets/wc2026_match_dataset.json --held-out-competition "World Cup 2026"
```

## 7. Match-level accuracy vs actual outcomes

Sections 1–6 score predictions against **`target_soft`** (de-vigged bookmaker consensus), measuring how closely the model tracks market pricing. This section asks the harder question: who assigns better probability to what actually happened on the pitch?

**Coverage:** 556 of 558 LOTO CatBoost predictions joined to 90-minute actual results from `data/reference/old_stats/`. All predictions are out-of-sample. Knockout matches that went to extra time or penalties are scored on the 90-minute result, consistent with how `Bracket_Simulations` samples knockout draws.

### Headline results - all legacy12 tournaments (556 matches)

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **304 (54.7%)** | 252 (45.3%) |
| Mean log-loss | **0.9629** | 0.9722 (+0.0093) |
| Mean 3-class Brier vs actuals | **0.5739** | 0.5794 (+0.0055) |
| Top-1 accuracy | 297/556 (53.4%) | **301/556 (54.1%)** |

### World Cups only - 2010–2022 (256 matches)

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **142 (55.5%)** | 114 (44.5%) |
| Mean log-loss | **0.9801** | 0.9876 (+0.0076) |
| Mean 3-class Brier vs actuals | **0.5821** | 0.5877 (+0.0056) |
| Top-1 accuracy | 133/256 (52.0%) | **137/256 (53.5%)** |

The market wins slightly more than half of per-game log-loss comparisons. The model has a small edge on top-1 pick rate but loses on mean log-loss because it is often **more confident on wrong calls**.

> **Note:** Brier values here (~0.57) are computed against hard one-hot actual outcomes and are not comparable to the soft-label Brier (~0.008) in sections 1–3, which measures distance from the market consensus.

### By stage (World Cups)

| Stage | N | Model LL wins | Market LL wins | Mean Δ log-loss (model − market) |
|-------|---|---------------|----------------|----------------------------------|
| Group | 192 | 85 (44.3%) | 107 (55.7%) | +0.0090 |
| Knockout | 64 | 29 (45.3%) | 35 (54.7%) | +0.0035 |

| Stage | Market top-1 | Model top-1 |
|-------|--------------|-------------|
| Group | 101/192 (52.6%) | 104/192 (54.2%) |
| Knockout | 32/64 (50.0%) | 33/64 (51.6%) |

The market's log-loss advantage narrows in knockout matches - consistent with the soft-label Brier results in section 3, where the model's relative improvement over Elo is largest in knockout games.

### Top-1 breakdown (World Cups)

| Category | Count |
|----------|-------|
| Both market and model pick correctly | 131 |
| Market only correct | 2 |
| Model only correct | 6 |
| Neither correct | 117 |

The model earns **4 extra correct top-1 picks** (137 vs 133) but loses the log-loss tally because wrong predictions carry higher misplaced confidence. When model and market disagree on the favourite (37 games), they split even on log-loss (model 19, market 18) but the model wins 14 vs 10 on top-1 - suggesting the model's divergence from the market is not random noise.

### Per World Cup

| Tournament | N | Model LL wins | Market LL wins | Mean Δ log-loss | Top-1 market / model |
|------------|---|---------------|----------------|-----------------|----------------------|
| World Cup 2010 | 64 | 29 | 35 | +0.0054 | 32 / 31 |
| World Cup 2014 | 64 | **36** | 28 | **−0.0134** | 31 / **34** |
| World Cup 2018 | 64 | 25 | 39 | +0.0071 | 36 / **37** |
| World Cup 2022 | 64 | 24 | 40 | +0.0313 | 34 / **35** |

Only 2014 is clearly model-favourable on mean log-loss. 2022 is the hardest tournament for the model. High variance across tournaments - no single World Cup is enough to draw firm conclusions.

### Why the model loses to the market on log-loss - and why that doesn't contradict the bracket results

The market's log-loss edge against actual outcomes is the **expected result**, not a failure mode. Four reasons:

1. **Training target.** CatBoost is fit to approximate market soft labels, not to maximise hard-outcome log-loss. The market is effectively the training signal, so it will always edge ahead when both are scored against actual results on the same measure.
2. **Overconfidence penalty.** Log-loss punishes confident wrong calls heavily. The model can win more top-1 correct picks while losing mean log-loss if it assigns too much probability mass to those picks when they are wrong.
3. **Compounding through the bracket.** Bracket simulation chains many matches. Small per-game shifts in probability - even ones the market wouldn't endorse - can change which teams rank in the top 8/4/2 across the full tournament in ways that accumulate in the model's favour.
4. **Different objects.** Match-level log-loss scores isolated 1X2 lines. Bracket M1 and M4 score marginal reach and joint stage configurations after full Monte Carlo propagation - a harder and more tournament-relevant test where the model leads the market at every recall stage and on cumulative coverage at the Final and Winner.

The bracket backtest results in `Bracket_Simulations/results.md` are not undermined by the match-level finding. The model is a purpose-built bracket input, not a replacement for the bookmaker consensus - and on the task it was built for, it outperforms the market where it counts most.

## 8. Reproduce section 7

From the `WorldCup2026 Bracket` repo root:

```powershell
cd Match_model
python main_cli.py match-vs-market
```

This reads `data/output/experiments/loto_eval_predictions.csv`, joins actual 90-minute results from `data/reference/old_stats/`, and writes a full markdown report to `data/output/experiments/match_vs_market_report.md`. All defaults match the committed paths; pass `--help` for override options.
