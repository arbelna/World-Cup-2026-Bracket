# Bracket_Simulations - historical backtest summary

**Generated:** 2026-06-03 10:18 UTC | **Tournaments:** 4 (WC 2010-2022) | **Modes:** `market_all` vs `model_all`

> This is the curated reader-facing summary. The detailed generated report lives in `data/output/simulations/stage_prediction_backtest.md`.

## Key findings

- `model_all` edges `market_all` on average M1 top-N recall at R16 (71.88% vs 70.31%), QF (65.62% vs 62.50%), SF (50.00% vs 43.75%), and final (37.50% vs 25.00%).
- M2 is `0/4` for both modes at every stage: the rank-1 exact bracket never matches reality, which is a concise reminder that exact bracket configurations are far more brittle than marginal stage probabilities.
- M3 cumulative (lower is better): when the exact set was never simulated, both modes report 99.90%; otherwise compare observed ranks in the per-tournament tables.
- Both modes miss the actual champion as the top-1 winner pick in all four tournaments, but both still keep the actual champion relatively near the front of the winner distribution on average (M3 winner rank 4 for market and 4 for model).

## How to read the metrics

- M1: top-N marginal recall from `p_at_least_{stage}`; higher is better.
- M2: whether the single most likely exact team set matched reality; `yes` or `no`.
- M3: cumulative probability up to the exact actual set; lower is better, and 99.90% means the exact set was never observed in the simulated support.
- M4: cumulative probability until every actual team has appeared somewhere in the high-probability joint support; lower is better.

## M1 recall edge

| Stage | Market M1 recall | Model M1 recall | Delta pp (model - market) | Better side |
|-------|------------------|-----------------|---------------------------|-------------|
| **R16** | 70.31% | 71.88% | +1.56 | model |
| **QF** | 62.50% | 65.62% | +3.12 | model |
| **SF** | 43.75% | 50.00% | +6.25 | model |
| **final** | 25.00% | 37.50% | +12.50 | model |

`model_all` holds a small but consistent aggregate M1 recall edge from R16 through final in the historical backtest.

## Aggregate

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|
| **R16** | 70.31% | 71.88% | 0/4 | 0/4 | 62.05% | 97.21% | 9.29% | 6.24% |
| **QF** | 62.50% | 65.62% | 0/4 | 0/4 | 40.01% | 59.74% | 14.38% | 15.75% |
| **SF** | 43.75% | 50.00% | 0/4 | 0/4 | 45.02% | 42.47% | 24.11% | 27.19% |
| **final** | 25.00% | 37.50% | 0/4 | 0/4 | 39.12% | 25.39% | 35.91% | 19.60% |
| **winner** | 0.00% | 0.00% | 0/4 | 0/4 | 56.86% | 43.39% | 56.86% | 43.39% |

| Stage | M3 avg rank mkt | M3 avg rank mdl | M4 avg rank mkt | M4 avg rank mdl |
|-------|-----------------|-----------------|-----------------|-----------------|
| **R16** | 20432 | 75614 | 194 | 213 |
| **QF** | 1234 | 32340 | 134 | 782 |
| **SF** | 287 | 382 | 47 | 152 |
| **final** | 13 | 12 | 10 | 8 |
| **winner** | 4 | 4 | 4 | 4 |

## World Cup 2010 (`wc2010`)

**Champion (actual):** Spain
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|
| **R16** | 12/16 | 11/16 | no | no | 55.52% | 89.14% |
| **QF** | 5/8 | 5/8 | no | no | 34.27% | 98.33% |
| **SF** | 1/4 | 1/4 | no | no | 37.15% | 51.44% |
| **final** | 1/2 | 1/2 | no | no | 28.19% | 27.12% |
| **winner** | 0/1 | 0/1 | no | no | 34.84% | 35.34% |

_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%)._

## World Cup 2014 (`wc2014`)

**Champion (actual):** Germany
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|
| **R16** | 10/16 | 11/16 | no | no | 99.90% | 99.90% |
| **QF** | 5/8 | 5/8 | no | no | 43.62% | 99.90% |
| **SF** | 3/4 | 2/4 | no | no | 13.93% | 34.22% |
| **final** | 0/2 | 1/2 | no | no | 21.07% | 13.94% |
| **winner** | 0/1 | 0/1 | no | no | 50.44% | 64.26% |

_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%)._

## World Cup 2018 (`wc2018`)

**Champion (actual):** France
- Market winner pick: Germany
- Model winner pick: England

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|
| **R16** | 14/16 | 13/16 | no | no | 24.55% | 99.90% |
| **QF** | 4/8 | 5/8 | no | no | 52.24% | 9.18% |
| **SF** | 1/4 | 3/4 | no | no | 41.96% | 5.34% |
| **final** | 0/2 | 0/2 | no | no | 76.42% | 54.00% |
| **winner** | 0/1 | 0/1 | no | no | 66.02% | 46.23% |

_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%)._

## World Cup 2022 (`wc2022`)

**Champion (actual):** Argentina
- Market winner pick: Brazil
- Model winner pick: Portugal

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|
| **R16** | 9/16 | 11/16 | no | no | 68.25% | 99.90% |
| **QF** | 6/8 | 6/8 | no | no | 29.92% | 31.55% |
| **SF** | 2/4 | 2/4 | no | no | 87.03% | 78.88% |
| **final** | 1/2 | 1/2 | no | no | 30.82% | 6.51% |
| **winner** | 0/1 | 0/1 | no | no | 76.15% | 27.74% |

_M1 = top-N marginal recall; M2 = rank-1 exact set match (yes/no); M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%)._

## Worked example - WC 2022 SF (model)

| | Metric 3 (exact set) | Metric 4 (all teams seen) |
|--|----------------------|---------------------------|
| Target | Argentina, Croatia, France, Morocco | Same four teams, any combo |
| Stop rank | 964 | **429** |
| Cumulative | 78.88% | **61.33%** |
| Trigger combo | exact quartet | Argentina, France, Morocco, Portugal (Morocco last) |

At rank 429 the model has seen every actual SF team at least once, but only 61.33% of simulated mass; the exact quartet needs rank 964 (78.88%).

Union at rank 429 (**21** teams): all four actual plus 17 others that appeared in high-frequency SF combos (see WC 2022 -> SF -> Metric 4 -> Model).

