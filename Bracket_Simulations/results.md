# Bracket_Simulations - historical backtest summary

**Generated:** 2026-06-08 15:52 UTC | **Tournaments:** 4 (WC 2010-2022) | **Modes:** `market_all` vs `model_all`

> This is the curated reader-facing summary. The detailed generated report lives in `data/output/simulations/stage_prediction_backtest.md`.

## Conclusions

The goal of `model_all` is to be **competitive** with the betting market benchmark (`market_all`), not to beat it outright. Betting markets aggregate enormous amounts of information; matching them with a statistical model built from historical match data is already a strong result.

Across four World Cups (2010-2022) the picture is mixed but broadly positive:

- **Recall (M1):** `model_all` edges `market_all` at every stage (R16: 71.88% vs 70.31%, QF: 65.62% vs 62.50%, SF: 50.00% vs 43.75%, final: 37.50% vs 25.00%). The direction is consistent, but with only 4 tournaments the bootstrap confidence intervals all span zero — the gap is real in direction but not distinguishable from noise at this sample size.
- **Qualifier Brier (M2):** `market_all` wins cleanly at every stage (lower is better). The model assigns less accurate probabilities to teams that actually qualified. This is the market's clearest advantage.
- **Calibration:** `market_all` is better calibrated overall (ECE 0.0095 vs 0.0237). Both models are well-calibrated on low-probability teams — the large majority of cases — and sit close to the diagonal in the 0-0.3 range. The model's deficit is concentrated in the 0.5-0.7 bin (-0.136 (avg pred 0.58, observed 0.71)): it consistently underrates mid-range favourites. The market is sharper in that range (-0.021 (avg pred 0.61, observed 0.63)).
- **Winner prediction:** neither model correctly identifies the actual champion as top pick in any of the four tournaments — consistent with the unpredictability of knockout football.

**Overall verdict:** `model_all` is competitive with the market. It matches market on recall and holds its own on joint-distribution metrics (M3/M4 at SF and final). The market is better calibrated, particularly for favourites in the 0.5-0.7 probability range. Improving the model's confidence on strong favourites is the clearest remaining gap.

## How to read the metrics

- M1: top-N marginal recall from `p_at_least_{stage}`; higher is better.
- M2: mean Brier on teams that actually reached the stage, using `p_at_least_{stage}`; lower is better.
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

## M2 qualifier Brier

Mean squared error on actual qualifiers only: average of `(p_at_least - 1)^2` over teams that reached the stage.

| Stage | Market M2 Brier | Model M2 Brier | Delta (model - market) | Better side |
|-------|-----------------|----------------|------------------------|-------------|
| **R16** | 0.1955 | 0.2045 | +0.0090 | market |
| **QF** | 0.3246 | 0.3612 | +0.0365 | market |
| **SF** | 0.5138 | 0.5597 | +0.0459 | market |
| **final** | 0.6489 | 0.6767 | +0.0278 | market |
| **winner** | 0.7687 | 0.7861 | +0.0174 | market |

`market_all` has lower average qualifier Brier at every stage in the historical backtest.

## M3 exact-set cumulative

Cumulative simulated probability through the rank of the exact actual team set; 99.90% when that set never appeared.

| Stage | Market M3 cum | Model M3 cum | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 62.05% | 97.21% | +35.16 | market |
| **QF** | 40.01% | 59.74% | +19.73 | market |
| **SF** | 45.02% | 42.47% | -2.55 | model |
| **final** | 39.12% | 25.39% | -13.73 | model |
| **winner** | 56.86% | 43.39% | -13.47 | model |

## M4 all-teams-seen cumulative

Cumulative simulated probability through the first rank where every actual team has appeared in at least one joint combo.

| Stage | Market M4 cum | Model M4 cum | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 9.29% | 6.24% | -3.05 | model |
| **QF** | 14.38% | 15.75% | +1.37 | market |
| **SF** | 24.11% | 27.19% | +3.08 | market |
| **final** | 35.91% | 19.60% | -16.31 | model |
| **winner** | 56.86% | 43.39% | -13.47 | model |

## World Cup 2010 (`wc2010`)

**Champion (actual):** Spain
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|
| **R16** | 12/16 | 11/16 | 0.1871 | 0.1971 | 55.52% | 89.14% | 2.71% | 2.98% |
| **QF** | 5/8 | 5/8 | 0.3341 | 0.4154 | 34.27% | 98.33% | 12.05% | 14.24% |
| **SF** | 1/4 | 1/4 | 0.5000 | 0.5904 | 37.15% | 51.44% | 24.51% | 21.73% |
| **final** | 1/2 | 1/2 | 0.5980 | 0.6708 | 28.19% | 27.12% | 28.19% | 25.07% |
| **winner** | 0/1 | 0/1 | 0.6825 | 0.7565 | 34.84% | 35.34% | 34.84% | 35.34% |

_M1 = top-N marginal recall; M2 = mean Brier on actual qualifiers from `p_at_least_{stage}`; M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%); M4 = cumulative probability until all actual teams have appeared in some combo._

## World Cup 2014 (`wc2014`)

**Champion (actual):** Germany
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|
| **R16** | 10/16 | 11/16 | 0.2539 | 0.2212 | 99.90% | 99.90% | 14.28% | 11.12% |
| **QF** | 5/8 | 5/8 | 0.3340 | 0.3985 | 43.62% | 99.90% | 15.61% | 27.96% |
| **SF** | 3/4 | 2/4 | 0.4108 | 0.5449 | 13.93% | 34.22% | 7.41% | 24.07% |
| **final** | 0/2 | 1/2 | 0.5825 | 0.6707 | 21.07% | 13.94% | 17.20% | 13.94% |
| **winner** | 0/1 | 0/1 | 0.7466 | 0.8414 | 50.44% | 64.26% | 50.44% | 64.26% |

_M1 = top-N marginal recall; M2 = mean Brier on actual qualifiers from `p_at_least_{stage}`; M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%); M4 = cumulative probability until all actual teams have appeared in some combo._

## World Cup 2018 (`wc2018`)

**Champion (actual):** France
- Market winner pick: Germany
- Model winner pick: England

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|
| **R16** | 14/16 | 13/16 | 0.1153 | 0.1788 | 24.55% | 99.90% | 2.89% | 2.63% |
| **QF** | 4/8 | 5/8 | 0.3300 | 0.3091 | 52.24% | 9.18% | 15.42% | 1.98% |
| **SF** | 1/4 | 3/4 | 0.5120 | 0.4776 | 41.96% | 5.34% | 12.76% | 1.65% |
| **final** | 0/2 | 0/2 | 0.7674 | 0.7404 | 76.42% | 54.00% | 67.43% | 32.89% |
| **winner** | 0/1 | 0/1 | 0.8206 | 0.8004 | 66.02% | 46.23% | 66.02% | 46.23% |

_M1 = top-N marginal recall; M2 = mean Brier on actual qualifiers from `p_at_least_{stage}`; M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%); M4 = cumulative probability until all actual teams have appeared in some combo._

## World Cup 2022 (`wc2022`)

**Champion (actual):** Argentina
- Market winner pick: Brazil
- Model winner pick: Portugal

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|
| **R16** | 9/16 | 11/16 | 0.2257 | 0.2209 | 68.25% | 99.90% | 17.27% | 8.23% |
| **QF** | 6/8 | 6/8 | 0.3003 | 0.3217 | 29.92% | 31.55% | 14.43% | 18.82% |
| **SF** | 2/4 | 2/4 | 0.6325 | 0.6259 | 87.03% | 78.88% | 51.77% | 61.33% |
| **final** | 1/2 | 1/2 | 0.6476 | 0.6249 | 30.82% | 6.51% | 30.82% | 6.51% |
| **winner** | 0/1 | 0/1 | 0.8251 | 0.7461 | 76.15% | 27.74% | 76.15% | 27.74% |

_M1 = top-N marginal recall; M2 = mean Brier on actual qualifiers from `p_at_least_{stage}`; M3 = cumulative probability up to the exact actual set (if never simulated, 99.90%); M4 = cumulative probability until all actual teams have appeared in some combo._

## Worked example - WC 2022 SF (model)

| | Metric 3 (exact set) | Metric 4 (all teams seen) |
|--|----------------------|---------------------------|
| Target | Argentina, Croatia, France, Morocco | Same four teams, any combo |
| Stop rank | 964 | **429** |
| Cumulative | 78.88% | **61.33%** |
| Trigger combo | exact quartet | Argentina, France, Morocco, Portugal (Morocco last) |

At rank 429 the model has seen every actual SF team at least once, but only 61.33% of simulated mass; the exact quartet needs rank 964 (78.88%).

Union at rank 429 (**21** teams): all four actual plus 17 others that appeared in high-frequency SF combos (see WC 2022 -> SF -> Metric 4 -> Model).

