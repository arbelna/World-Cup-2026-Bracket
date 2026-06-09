# Match_model - detailed LOTO results

**Generated:** 2026-06-09 09:46 UTC
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
| catboost_loto_core7 | 0.9641 | 0.0097 | 0.0417 |
| catboost_loto_elo_only | 0.9771 | 0.0185 | 0.0586 |
| catboost_loto_elo_plus_values | 0.9662 | 0.0111 | 0.0448 |
| catboost_loto_minus_values | 0.9723 | 0.0152 | 0.0536 |
| catboost_loto_minus_confed | 0.9643 | 0.0099 | 0.0425 |
| catboost_loto_minus_stage | 0.9644 | 0.0099 | 0.0424 |
| catboost_loto_minus_host | 0.9665 | 0.0113 | 0.0451 |
| baseline__elo | 0.9808 | 0.0205 | 0.0645 |
| baseline__marginal | 1.0604 | 0.0768 | 0.1224 |
| baseline__market_dispersion | 0.9517 | 0.0016 | 0.0144 |

**CatBoost vs Elo baseline (weighted CE):** 0.9641 vs 0.9808 (delta = -0.0168; negative delta means CatBoost is better).
`baseline__market_dispersion` can score better than CatBoost on CE because it reads market-price dispersion directly while the target is itself the de-vigged market consensus. Treat it as a market-aware calibration reference, not a fair standalone predictive baseline; the cleaner predictive comparison is CatBoost versus `baseline__elo`.

## 1b. What the errors look like on one 1X2 line

The leaderboard MAE is a macro average over home, draw, and away: for each outcome, take |model - market|, then average the three. It is **not** the gap on the favorite alone.

CatBoost's weighted MAE is **4.17 percentage points** per outcome on average (0.0417 on the 0-1 scale). The table below uses that exact average on one illustrative de-vigged 1X2 line (favorite probability softens; draw and away share the shift):

| Outcome | Market | Model | Delta pp (model - market) | Abs error |
|---------|--------|-------|---------------------------|-----------|
| Home win | 70.0% | 63.7% | -6.3 | 6.3 |
| Draw | 20.0% | 23.1% | +3.1 | 3.1 |
| Away win | 10.0% | 13.2% | +3.2 | 3.2 |
| **Macro MAE** | | | | **4.20** |

The favorite is still home, but the model is 6.3 pp less confident; draw and away gain 3.1 pp and 3.2 pp. Macro MAE on this line is **4.20 pp**, matching the headline **4.17 pp**.

Brier squares those same three gaps before averaging, so it punishes large misses more heavily; cross-entropy punishes confident wrong calls even more. None of the three numbers is a bracket probability by itself - they are per-match 1X2 inputs that feed the pairwise simulation stage.

## 2. Per-tournament held-out errors

Each row is one leave-one-tournament-out fold: train on 11 tournaments, test on the held-out competition. Negative deltas mean CatBoost beat the Elo baseline on that metric.

| Tournament | N | CatBoost CE | Elo CE | delta CE vs Elo | CatBoost Brier | Elo Brier | delta Brier vs Elo |
|------------|---|-------------|--------|-----------------|----------------|-----------|--------------------|
| Copa America 2016 | 32 | 0.9273 | 0.9432 | -0.0158 | 0.0120 | 0.0227 | -0.0107 |
| Copa America 2019 | 26 | 0.9183 | 0.9426 | -0.0243 | 0.0201 | 0.0368 | -0.0167 |
| Copa America 2021 | 28 | 0.9191 | 0.9343 | -0.0153 | 0.0102 | 0.0202 | -0.0100 |
| Copa America 2024 | 32 | 0.9237 | 0.9435 | -0.0198 | 0.0093 | 0.0216 | -0.0122 |
| Euro 2012 | 31 | 1.0315 | 1.0518 | -0.0203 | 0.0122 | 0.0258 | -0.0136 |
| Euro 2016 | 51 | 1.0019 | 1.0101 | -0.0082 | 0.0097 | 0.0144 | -0.0048 |
| Euro 2020 | 51 | 0.9600 | 0.9812 | -0.0212 | 0.0071 | 0.0210 | -0.0139 |
| Euro 2024 | 51 | 0.9709 | 0.9839 | -0.0129 | 0.0085 | 0.0168 | -0.0083 |
| World Cup 2010 | 64 | 0.9761 | 0.9933 | -0.0172 | 0.0087 | 0.0193 | -0.0106 |
| World Cup 2014 | 64 | 0.9784 | 0.9882 | -0.0099 | 0.0103 | 0.0170 | -0.0068 |
| World Cup 2018 | 64 | 0.9626 | 0.9831 | -0.0204 | 0.0071 | 0.0205 | -0.0134 |
| World Cup 2022 | 64 | 0.9510 | 0.9719 | -0.0209 | 0.0091 | 0.0219 | -0.0127 |

- **Best CE vs Elo:** Copa America 2019 (-0.0243)
- **Worst CE vs Elo:** Euro 2016 (-0.0082)
- **Best Brier vs Elo:** Copa America 2019 (-0.0167)
- **Worst Brier vs Elo:** Euro 2016 (-0.0048)

## 3. Group stage vs knockout matches

The table below splits the held-out match predictions by stage bucket. This is useful because group matches carry more draw mass, while knockout matches compress the draw problem into a smaller set of usually stronger teams.

| Bucket | N | CatBoost CE | Elo CE | CatBoost Brier | Elo Brier | CatBoost MAE | Elo MAE |
|--------|---|-------------|--------|----------------|-----------|--------------|---------|
| group | 410 | 0.9518 | 0.9706 | 0.0107 | 0.0227 | 0.0440 | 0.0680 |
| knockout | 148 | 0.9980 | 1.0093 | 0.0069 | 0.0143 | 0.0355 | 0.0549 |

- **Group large-miss example:** Italy vs Ireland - the model's top call was Italy at 42.2%, while the market target's top call was Italy at 68.4%; the largest probability miss was 26.2 percentage points.
- **Knockout large-miss example:** Costa Rica vs Greece - the model's top call was Greece at 55.0%, while the market target's top call was Costa Rica at 34.9%; the largest probability miss was 21.3 percentage points.

## 4. Ablation and sensitivity analysis

These fixed ablations test whether the match-level gains depend on a single feature block. Negative deltas are better for cross-entropy and Brier because the base `core7` model is the reference.

### Historical LOTO

| Variant | CE | delta CE vs base | Brier | delta Brier vs base | MAE |
|---------|----|------------------|-------|---------------------|-----|
| Base core7 | 0.9641 | +0.0000 | 0.0097 | +0.0000 | 0.0417 |
| Elo only | 0.9771 | +0.0131 | 0.0185 | +0.0088 | 0.0586 |
| Elo plus squad values | 0.9662 | +0.0021 | 0.0111 | +0.0014 | 0.0448 |
| Remove squad values | 0.9723 | +0.0082 | 0.0152 | +0.0055 | 0.0536 |
| Remove confederation | 0.9643 | +0.0003 | 0.0099 | +0.0002 | 0.0425 |
| Remove stage context | 0.9644 | +0.0003 | 0.0099 | +0.0002 | 0.0424 |
| Remove host advantage | 0.9665 | +0.0025 | 0.0113 | +0.0016 | 0.0451 |

### WC2026 holdout

| Variant | CE | delta CE vs base | Brier | delta Brier vs base | MAE |
|---------|----|------------------|-------|---------------------|-----|
| Base core7 | 0.9214 | +0.0000 | 0.0065 | +0.0000 | 0.0356 |
| Elo only | 0.9405 | +0.0191 | 0.0193 | +0.0128 | 0.0565 |
| Elo plus squad values | 0.9225 | +0.0011 | 0.0073 | +0.0008 | 0.0380 |
| Remove squad values | 0.9280 | +0.0066 | 0.0110 | +0.0044 | 0.0429 |
| Remove confederation | 0.9210 | -0.0004 | 0.0063 | -0.0003 | 0.0348 |
| Remove stage context | 0.9215 | +0.0001 | 0.0066 | +0.0001 | 0.0362 |
| Remove host advantage | 0.9212 | -0.0002 | 0.0064 | -0.0001 | 0.0353 |

The largest historical degradation comes from **elo only** (delta CE +0.0131). This is the quickest read on which block the base model is leaning on most heavily.

## 5. Highest cross-entropy predictions (CatBoost)

These are the 10 worst single-match CatBoost CE errors on held-out folds. The comparison below focuses on the market call, the model call, and the actual 90-minute result from the vendored historical text files.

| # | Match | Stage | Actual 90m | Market top call | Model top call | CE | Brier |
|---|-------|-------|------------|-----------------|----------------|----|-------|
| 1 | Colombia vs Paraguay | group | Colombia win (1-0) | Colombia 39.7% (hit) | Colombia 63.0% (hit) | 1.2241 | 0.0879 |
| 2 | Costa Rica vs Greece | knockout | Draw (1-1) | Costa Rica 34.9% (miss) | Greece 55.0% (miss) | 1.2111 | 0.0759 |
| 3 | Turkey vs Czechia | group | Turkey win (2-0) | Czechia 41.1% (miss) | Turkey 50.8% (hit) | 1.1929 | 0.0735 |
| 4 | South Africa vs Mexico | group | Draw (1-1) | Mexico 37.9% (miss) | Mexico 58.2% (miss) | 1.1834 | 0.0637 |
| 5 | Poland vs Japan | group | Poland win (1-0) | Poland 35.8% (hit) | Poland 53.0% (hit) | 1.1652 | 0.0476 |
| 6 | Mexico vs Uruguay | group | Mexico win (3-1) | Mexico 38.6% (hit) | Uruguay 46.2% (miss) | 1.1604 | 0.0473 |
| 7 | South Africa vs France | group | South Africa win (2-1) | France 45.0% (miss) | France 64.5% (miss) | 1.1574 | 0.0587 |
| 8 | Bosnia and Herzegovina vs Iran | group | Bosnia and Herzegovina win (3-1) | Bosnia and Herzegovina 42.8% (hit) | Bosnia and Herzegovina 59.3% (hit) | 1.1553 | 0.0480 |
| 9 | Japan vs Senegal | group | Draw (2-2) | Senegal 36.7% (miss) | Senegal 52.6% (miss) | 1.1501 | 0.0390 |
| 10 | South Africa vs Uruguay | group | Uruguay win (0-3) | Uruguay 40.7% (hit) | Uruguay 57.6% (hit) | 1.1462 | 0.0433 |

1. **Shared pattern in 4 matches**: Colombia vs Paraguay, South Africa vs Mexico, South Africa vs France, South Africa vs Uruguay. In each case, a large Elo gap appears to have pulled the model too hard toward one side.
2. **Costa Rica vs Greece**: The model flipped the favorite relative to the market consensus.
3. **Turkey vs Czechia**: The model flipped the favorite relative to the market consensus.
4. **Poland vs Japan**: The model and market leaned the same way, but the model concentrated too much probability mass.
5. **Mexico vs Uruguay**: The model flipped the favorite relative to the market consensus.
6. **Bosnia and Herzegovina vs Iran**: The model and market leaned the same way, but the model concentrated too much probability mass.
7. **Japan vs Senegal**: The model and market leaned the same way, but the model concentrated too much probability mass.

## 6. WC2026 explicit holdout (train legacy12, test WC2026)

Train/test split evaluation with train set from legacy12 and held-out test set `World Cup 2026`.
WC2026 test dataset: `data/output/datasets/wc2026_match_dataset.json`

| Experiment | CE | Brier | MAE |
|------------|----|-------|-----|
| catboost_loto_core7 | 0.9214 | 0.0065 | 0.0356 |
| catboost_loto_elo_only | 0.9405 | 0.0193 | 0.0565 |
| catboost_loto_elo_plus_values | 0.9225 | 0.0073 | 0.0380 |
| catboost_loto_minus_values | 0.9280 | 0.0110 | 0.0429 |
| catboost_loto_minus_confed | 0.9210 | 0.0063 | 0.0348 |
| catboost_loto_minus_stage | 0.9215 | 0.0066 | 0.0362 |
| catboost_loto_minus_host | 0.9212 | 0.0064 | 0.0353 |
| baseline__elo | 0.9479 | 0.0228 | 0.0633 |
| baseline__marginal | 1.0769 | 0.1166 | 0.1426 |
| baseline__market_dispersion | 0.9126 | 0.0008 | 0.0120 |
| reference__market_target_oracle | 0.9110 | 0.0000 | 0.0000 |

CatBoost vs Elo on `World Cup 2026` (CE): 0.9214 vs 0.9479 (delta -0.0265, negative means CatBoost is better).

Historical CatBoost ranges across the 12 LOTO folds: CE 0.9183-1.0315, Brier 0.0071-0.0201, and CE delta vs Elo -0.0243 to -0.0082. The WC2026 holdout lands at CE 0.9214, Brier 0.0065, and delta -0.0265.
That does not validate future outcomes, but it does suggest the WC2026 pairwise probability surface behaves like the historical tournament folds rather than like an obvious outlier, so these predictions are reasonable inputs for the bracket simulation stage.

**WC2026 holdout example** (CatBoost weighted MAE **3.56 pp** on the test set):

| Outcome | Market | Model | Delta pp (model - market) | Abs error |
|---------|--------|-------|---------------------------|-----------|
| Home win | 58.0% | 52.7% | -5.3 | 5.3 |
| Draw | 26.0% | 28.7% | +2.7 | 2.7 |
| Away win | 16.0% | 18.6% | +2.6 | 2.6 |
| **Macro MAE** | | | | **3.53** |

On a representative group-stage line, home stays the favorite but drops 5.3 pp while draw and away rise 2.7 pp and 2.6 pp. Macro MAE on this line is **3.53 pp**, matching the WC2026 holdout **3.56 pp**.

## 7. Match-level model vs market - scored against 90-minute actual outcomes

CatBoost LOTO predictions scored against the 90-minute result. The market predictor is the de-vigged bookmaker consensus (`target_soft`); the model predictor is the out-of-sample CatBoost `core7` prediction. Knockout matches that went to extra time or penalties are scored on the 90-minute result. Full report: `data/output/experiments/match_vs_market_report.md`.

### All legacy12 tournaments (558 matches)

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **305 (54.7%)** | 253 (45.3%) |
| Mean log-loss | **0.9631** | 0.9726 (+0.0095) |
| Mean 3-class Brier vs actuals | **0.5739** | 0.5795 (+0.0056) |
| Top-1 accuracy | 298/558 (53.4%) | **302/558 (54.1%)** |

### World Cups only - 2010-2022 (256 matches)

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **142 (55.5%)** | 114 (44.5%) |
| Mean log-loss | **0.9801** | 0.9876 (+0.0076) |
| Mean 3-class Brier vs actuals | **0.5821** | 0.5877 (+0.0056) |
| Top-1 accuracy | 133/256 (52.0%) | **137/256 (53.5%)** |

The market wins slightly more per-game log-loss comparisons. The model has a +4 top-1 edge on World Cup matches (137 vs 133), picking the right favourite more often even while trailing on mean log-loss (it is more confident on some wrong calls).

### By stage (World Cups)

| Stage | N | Model LL wins | Market LL wins | Mean delta log-loss (model - market) |
|-------|---|---------------|----------------|--------------------------------------|
| Group | 192 | 85 (44.3%) | 107 (55.7%) | +0.0090 |
| Knockout | 64 | 29 (45.3%) | 35 (54.7%) | +0.0035 |

| Stage | Market top-1 | Model top-1 |
|-------|--------------|-------------|
| Group | 101/192 (52.6%) | 104/192 (54.2%) |
| Knockout | 32/64 (50.0%) | 33/64 (51.6%) |

### Elo vs CatBoost vs market (World Cups)

| Predictor | Beats market (log-loss) | Mean log-loss | Top-1 correct |
|-----------|-------------------------|---------------|---------------|
| **Market** | - | **0.9801** | 133/256 |
| **CatBoost** | 114/256 (44.5%) | 0.9876 | **137/256** |
| **Elo** | 109/256 (42.6%) | 0.9871 | 141/256 |

> **Note:** Brier values here (~0.57) are computed against hard one-hot actual outcomes and are not comparable to the soft-label Brier (~0.008) in the LOTO leaderboard, which measures distance from the market consensus.
