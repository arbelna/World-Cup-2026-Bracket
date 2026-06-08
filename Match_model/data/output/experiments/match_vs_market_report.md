# Match-level model vs market vs actual outcomes

**Generated:** 2026-06-08 15:02 UTC
**Scope:** 556 LOTO CatBoost predictions scored against 90-minute actual results.

For each match the market probability is the de-vigged bookmaker consensus (`target_soft`). The model probability is the CatBoost `core7` LOTO out-of-sample prediction. Knockout matches that went to extra time or penalties are scored on the 90-minute result.

## All legacy12 tournaments

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **304 (54.7%)** | 252 (45.3%) |
| Mean log-loss | **0.9629** | 0.9722 (+0.0093) |
| Mean 3-class Brier vs actuals | **0.5739** | 0.5794 (+0.0055) |
| Top-1 accuracy | 297/556 (53.4%) | **301/556 (54.1%)** |

## World Cups only — 2010–2022

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss head-to-head wins | **142 (55.5%)** | 114 (44.5%) |
| Mean log-loss | **0.9801** | 0.9876 (+0.0076) |
| Mean 3-class Brier vs actuals | **0.5821** | 0.5877 (+0.0056) |
| Top-1 accuracy | 133/256 (52.0%) | **137/256 (53.5%)** |

The market wins slightly more than half of per-game log-loss comparisons. The model has a small edge on top-1 pick rate but loses on mean log-loss because it is often **more confident on wrong calls**.

> **Note:** Brier values here (~0.57) are computed against hard one-hot actual outcomes and are not comparable to the soft-label Brier (~0.008) in the LOTO leaderboard, which measures distance from the market consensus.

## By stage (World Cups)

| Stage | N | Model LL wins | Market LL wins | Mean Δ log-loss (model − market) |
|-------|---|---------------|----------------|----------------------------------|
| Group | 192 | 85 (44.3%) | 107 (55.7%) | +0.0090 |
| Knockout | 64 | 29 (45.3%) | 35 (54.7%) | +0.0035 |

| Stage | Market top-1 | Model top-1 |
|-------|--------------|-------------|
| Group | 101/192 (52.6%) | 104/192 (54.2%) |
| Knockout | 32/64 (50.0%) | 33/64 (51.6%) |

## Top-1 breakdown (World Cups)

| Category | Count |
|----------|-------|
| Both market and model pick correctly | 131 |
| Market only correct | 2 |
| Model only correct | 6 |
| Neither correct | 117 |

The model earns **4 extra correct top-1 picks** (137 vs 133) but loses the log-loss tally because wrong predictions tend to carry higher misplaced confidence.

When model and market disagree on the favourite (13 games): log-loss essentially even (model 9, market 4 wins); model top-1 edge 6 vs 2.

## Per World Cup

| Tournament | N | Model LL wins | Market LL wins | Mean Δ log-loss | Top-1 market / model |
|------------|---|---------------|----------------|-----------------|----------------------|
| World Cup 2010 | 64 | 29 | 35 | +0.0054 | 32 / 31 |
| World Cup 2014 | 64 | 36 | 28 | -0.0134 | 31 / 34 |
| World Cup 2018 | 64 | 25 | 39 | +0.0071 | 36 / 37 |
| World Cup 2022 | 64 | 24 | 40 | +0.0313 | 34 / 35 |

## Elo vs CatBoost vs market (World Cups)

| Predictor | Beats market (log-loss) | Mean log-loss | Top-1 correct |
|-----------|-------------------------|---------------|---------------|
| **Market** | — | **0.9801** | 133/256 |
| **CatBoost** | 114/256 (44.5%) | 0.9876 | **137/256** |
| **Elo** | 109/256 (42.6%) | 0.9871 | 141/256 |
