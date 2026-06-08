# Bracket_Simulations - compare summary

> The concise historical backtest summary lives in [`results.md`](../../results.md). The detailed stage-by-stage backtest lives in `data/output/simulations/stage_prediction_backtest.md`.

Generated: 2026-06-08 14:44 UTC

Compares **market_all** (de-vigged bookmaker `target_soft`) vs **model_all** (core-7 CatBoost pairwise) against actual tournament outcomes for WC 2010-2022; WC 2026 forward comparison is included separately.

## Aggregate marginal metrics (Brier on `p_at_least_*`)

Lower Brier is better; for a single binary reach event, a 50/50 guess scores 0.25 and a perfect prediction scores 0.00.

| Stage | Market wins | Model wins | Ties |
|-------|-------------|------------|------|
| R16 | 2 | 2 | 0 |
| QF | 3 | 1 | 0 |
| SF | 2 | 2 | 0 |
| final | 2 | 2 | 0 |
| winner | 2 | 2 | 0 |

## Aggregate top-K hits

| Stage | Market wins | Model wins | Ties |
|-------|-------------|------------|------|
| R16 | 2 | 2 | 0 |
| QF | 0 | 1 | 3 |
| SF | 1 | 1 | 2 |
| final | 0 | 1 | 3 |
| winner | 0 | 0 | 4 |

**Champion top-1 correct:** market 0/4, model 0/4
**Avg p(winner) on actual champion:** market 12.39%, model 11.36%

## Joint stage-configuration metrics

For each stage, probability assigned to the exact set of teams that reached that stage in the actual tournament.

| Stage | Market avg p(actual) | Model avg p(actual) | Market top-1 hit | Model top-1 hit |
|-------|----------------------|---------------------|------------------|-----------------|
| R16 | 0.01% | 0.00% | 0/4 | 0/4 |
| QF | 0.02% | 0.01% | 0/4 | 0/4 |
| SF | 0.26% | 0.16% | 0/4 | 0/4 |
| final | 2.75% | 2.04% | 0/4 | 0/4 |
| winner | 12.39% | 11.36% | 0/4 | 0/4 |

## Market-reference comparisons (no actual outcomes yet)

For tournaments without played results, compare `model_all` probabilities against `market_all` reference probabilities on available stages.

| Tournament | Stage | MAE(model vs market) | MSE(model vs market) |
|------------|-------|----------------------|----------------------|
| World Cup 2026 | R32 | 0.0464 | 0.0038 |

## World Cup 2010 (wc2010)

Actual champion: **Spain**
- Market pick: Brazil (17.39% on actual)
- Model pick: Brazil (13.02% on actual)

### Marginal reach

| Stage | Metric | Market | Model | Better |
|-------|--------|--------|-------|--------|
| R16 | top-16 | 12.0000 | 11.0000 | market |
| R16 | Brier | 0.1829 | 0.1968 | market |
| QF | top-8 | 5.0000 | 5.0000 | tie |
| QF | Brier | 0.1252 | 0.1534 | market |
| SF | top-4 | 1.0000 | 1.0000 | tie |
| SF | Brier | 0.0857 | 0.0963 | market |
| final | top-2 | 1.0000 | 1.0000 | tie |
| final | Brier | 0.0459 | 0.0496 | market |
| winner | top-1 | 0.0000 | 0.0000 | tie |
| winner | Brier | 0.0241 | 0.0264 | market |

### Joint configurations

Teams that reached QF (8): Argentina, Brazil, Germany, Ghana, Netherlands, Paraguay, Spain, Uruguay

| Stage | p(actual) market | p(actual) model | Rank mkt | Rank mdl | Top-1 mkt | Top-1 mdl |
|-------|------------------|-----------------|----------|----------|-----------|-----------|
| R16 | 0.00% | 0.00% | 6758 | 56847 | no | no |
| QF | 0.01% | 0.00% | 1140 | 56842 | no | no |
| SF | 0.21% | 0.06% | 78 | 336 | no | no |
| final | 3.58% | 2.04% | 6 | 9 | no | no |
| winner | 17.39% | 13.02% | 2 | 2 | no | no |

## World Cup 2014 (wc2014)

Actual champion: **Germany**
- Market pick: Brazil (13.59% on actual)
- Model pick: Brazil (8.27% on actual)

### Marginal reach

| Stage | Metric | Market | Model | Better |
|-------|--------|--------|-------|--------|
| R16 | top-16 | 10.0000 | 11.0000 | model |
| R16 | Brier | 0.2446 | 0.2143 | model |
| QF | top-8 | 5.0000 | 5.0000 | tie |
| QF | Brier | 0.1236 | 0.1416 | market |
| SF | top-4 | 3.0000 | 2.0000 | market |
| SF | Brier | 0.0681 | 0.0848 | market |
| final | top-2 | 0.0000 | 1.0000 | model |
| final | Brier | 0.0444 | 0.0484 | market |
| winner | top-1 | 0.0000 | 0.0000 | tie |
| winner | Brier | 0.0265 | 0.0287 | market |

### Joint configurations

Teams that reached QF (8): Argentina, Belgium, Brazil, Colombia, Costa Rica, France, Germany, Netherlands

| Stage | p(actual) market | p(actual) model | Rank mkt | Rank mdl | Top-1 mkt | Top-1 mdl |
|-------|------------------|-----------------|----------|----------|-----------|-----------|
| R16 | 0.00% | 0.00% | 66270 | 92595 | no | no |
| QF | 0.01% | 0.00% | 2300 | 71276 | no | no |
| SF | 0.53% | 0.08% | 15 | 217 | no | no |
| final | 3.87% | 2.08% | 4 | 5 | no | no |
| winner | 13.59% | 8.27% | 3 | 6 | no | no |

## World Cup 2018 (wc2018)

Actual champion: **France**
- Market pick: Germany (9.41% on actual)
- Model pick: England (10.54% on actual)

### Marginal reach

| Stage | Metric | Market | Model | Better |
|-------|--------|--------|-------|--------|
| R16 | top-16 | 14.0000 | 13.0000 | market |
| R16 | Brier | 0.1198 | 0.1718 | market |
| QF | top-8 | 4.0000 | 5.0000 | model |
| QF | Brier | 0.1384 | 0.1168 | model |
| SF | top-4 | 1.0000 | 3.0000 | model |
| SF | Brier | 0.0928 | 0.0769 | model |
| final | top-2 | 0.0000 | 0.0000 | tie |
| final | Brier | 0.0600 | 0.0540 | model |
| winner | top-1 | 0.0000 | 0.0000 | tie |
| winner | Brier | 0.0297 | 0.0273 | model |

### Joint configurations

Teams that reached QF (8): Belgium, Brazil, Croatia, England, France, Russia, Sweden, Uruguay

| Stage | p(actual) market | p(actual) model | Rank mkt | Rank mdl | Top-1 mkt | Top-1 mdl |
|-------|------------------|-----------------|----------|----------|-----------|-----------|
| R16 | 0.04% | 0.00% | 293 | 88353 | no | no |
| QF | 0.01% | 0.03% | 1099 | 177 | no | no |
| SF | 0.30% | 0.47% | 64 | 9 | no | no |
| final | 0.63% | 1.01% | 34 | 32 | no | no |
| winner | 9.41% | 10.54% | 4 | 4 | no | no |

## World Cup 2022 (wc2022)

Actual champion: **Argentina**
- Market pick: Brazil (9.16% on actual)
- Model pick: Portugal (13.63% on actual)

### Marginal reach

| Stage | Metric | Market | Model | Better |
|-------|--------|--------|-------|--------|
| R16 | top-16 | 9.0000 | 11.0000 | model |
| R16 | Brier | 0.2207 | 0.2198 | model |
| QF | top-8 | 6.0000 | 6.0000 | tie |
| QF | Brier | 0.1172 | 0.1235 | market |
| SF | top-4 | 2.0000 | 2.0000 | tie |
| SF | Brier | 0.1060 | 0.1002 | model |
| final | top-2 | 1.0000 | 1.0000 | tie |
| final | Brier | 0.0503 | 0.0454 | model |
| winner | top-1 | 0.0000 | 0.0000 | tie |
| winner | Brier | 0.0298 | 0.0254 | model |

### Joint configurations

Teams that reached QF (8): Argentina, Brazil, Croatia, England, France, Morocco, Netherlands, Portugal

| Stage | p(actual) market | p(actual) model | Rank mkt | Rank mdl | Top-1 mkt | Top-1 mdl |
|-------|------------------|-----------------|----------|----------|-----------|-----------|
| R16 | 0.00% | 0.00% | 8405 | 64661 | no | no |
| QF | 0.03% | 0.01% | 399 | 1064 | no | no |
| SF | 0.01% | 0.02% | 990 | 964 | no | no |
| final | 2.90% | 3.04% | 7 | 2 | no | no |
| winner | 9.16% | 13.63% | 6 | 2 | no | no |

