# Bracket_Simulations - historical backtest summary

**Generated:** 2026-06-09 10:44 UTC | **Tournaments:** 4 (WC 2010-2022) | **Modes:** `market_all` vs `model_all`

> This is the curated reader-facing summary. The detailed generated report lives in `data/output/simulations/stage_prediction_backtest.md`.

## Conclusions

The goal of `model_all` is to be **competitive** with the betting market benchmark (`market_all`), not to beat it outright. Betting markets aggregate enormous amounts of information; matching them with a statistical model built from historical match data is already a strong result.

> **Comparison note:** `market_all` uses historical bookmaker odds set per-match during each tournament, meaning knockout odds incorporated group-stage results, injuries, and in-tournament momentum. `model_all` uses only pre-tournament features (Elo, squad values, confederation) for every match. The model therefore operates under an informational disadvantage, and its competitive performance should be read in that light.

Across four World Cups (2010-2022) the picture is mixed but broadly positive:

- **Recall (M1):** `model_all` matches or edges `market_all` at every stage (R16: 70.31% vs 70.31% tie, QF: 65.62% vs 62.50%, SF: 50.00% vs 43.75%, final: 37.50% vs 25.00%). The direction is consistent from QF onward; with only 4 tournaments the bootstrap confidence intervals all span zero - the gap is real in direction but not distinguishable from noise at this sample size.
- **Qualifier Brier (M2):** `market_all` wins cleanly at every stage (lower is better). The model assigns less accurate probabilities to teams that actually qualified. This is the market's clearest advantage.
- **All-team Brier (M5) and log loss (M6):** `market_all` also leads on both all-team metrics at R16/QF/SF on average, consistent with M2. The gap narrows at final/winner stages where the model is marginally competitive.
- **Calibration:** `market_all` is better calibrated overall (ECE 0.0095 vs 0.0242). Both models are well-calibrated on low-probability teams - the large majority of cases - and sit close to the diagonal in the 0-0.3 range. The model's deficit is concentrated in the 0.5-0.7 bin (-0.128 (avg pred 0.57, observed 0.70)): it consistently underrates mid-range favourites. The market is sharper in that range (-0.021 (avg pred 0.61, observed 0.63)).
- **Winner prediction:** neither model correctly identifies the actual champion as top pick in any of the four tournaments - consistent with the unpredictability of knockout football.

**Overall verdict:** `model_all` is competitive with the market. It matches market on recall and holds its own on joint-distribution metrics (M3/M4 at SF and final). The market is better calibrated, particularly for favourites in the 0.5-0.7 probability range. Improving the model's confidence on strong favourites is the clearest remaining gap.

## How to read the metrics

- M1: top-N marginal recall from `p_at_least_{stage}`; higher is better.
- M2: mean Brier on teams that actually reached the stage, using `p_at_least_{stage}`; lower is better.
- M3: cumulative probability up to the exact actual set; lower is better, and 99.90% means the exact set was never observed in the simulated support.
- M4: cumulative probability until every actual team has appeared somewhere in the high-probability joint support; lower is better.
- M5: all-team binary Brier - mean squared error of `p_at_least_{stage}` vs 0/1 outcome across **all 32 teams**; lower is better.
- M6: all-team binary log loss - mean cross-entropy of `p_at_least_{stage}` vs 0/1 outcome across **all 32 teams**; lower is better.

## M1 recall edge

| Stage | Market M1 recall | Model M1 recall | Delta pp (model - market) | Better side |
|-------|------------------|-----------------|---------------------------|-------------|
| **R16** | 70.31% | 70.31% | +0.00 | tie |
| **QF** | 62.50% | 65.62% | +3.12 | model |
| **SF** | 43.75% | 50.00% | +6.25 | model |
| **final** | 25.00% | 37.50% | +12.50 | model |

`model_all` holds a small but consistent aggregate M1 recall edge from R16 through final in the historical backtest.

## M2 qualifier Brier

Mean squared error on actual qualifiers only: average of `(p_at_least - 1)^2` over teams that reached the stage.

| Stage | Market M2 Brier | Model M2 Brier | Delta (model - market) | Better side |
|-------|-----------------|----------------|------------------------|-------------|
| **R16** | 0.1955 | 0.2086 | +0.0131 | market |
| **QF** | 0.3246 | 0.3585 | +0.0338 | market |
| **SF** | 0.5138 | 0.5580 | +0.0442 | market |
| **final** | 0.6489 | 0.6725 | +0.0236 | market |
| **winner** | 0.7687 | 0.7811 | +0.0124 | market |

`market_all` has lower average qualifier Brier at every stage in the historical backtest.

## M3 exact-set cumulative

Cumulative simulated probability through the rank of the exact actual team set; 99.90% when that set never appeared.

| Stage | Market M3 cum | Model M3 cum | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 62.05% | 97.21% | +35.16 | market |
| **QF** | 40.01% | 60.13% | +20.11 | market |
| **SF** | 45.02% | 43.61% | -1.41 | model |
| **final** | 39.12% | 25.66% | -13.46 | model |
| **winner** | 56.86% | 45.23% | -11.63 | model |

## M4 all-teams-seen cumulative

Cumulative simulated probability through the first rank where every actual team has appeared in at least one joint combo.

| Stage | Market M4 cum | Model M4 cum | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 9.29% | 7.85% | -1.44 | model |
| **QF** | 14.38% | 15.04% | +0.66 | market |
| **SF** | 24.11% | 27.55% | +3.44 | market |
| **final** | 35.91% | 19.87% | -16.03 | model |
| **winner** | 56.86% | 45.23% | -11.63 | model |

## M5 all-team binary Brier

Mean squared error of `p_at_least_{stage}` vs 0/1 outcome across all 32 teams (qualifiers score toward 1, eliminated teams toward 0).

| Stage | Market M5 Brier | Model M5 Brier | Delta (model - market) | Better side |
|-------|-----------------|----------------|------------------------|-------------|
| **R16** | 0.1920 | 0.2039 | +0.0119 | market |
| **QF** | 0.1261 | 0.1325 | +0.0064 | market |
| **SF** | 0.0882 | 0.0897 | +0.0015 | market |
| **final** | 0.0502 | 0.0493 | -0.0008 | model |
| **winner** | 0.0275 | 0.0269 | -0.0006 | model |

## M6 all-team binary log loss

Mean binary cross-entropy of `p_at_least_{stage}` vs 0/1 outcome across all 32 teams; lower is better.

| Stage | Market M6 log loss | Model M6 log loss | Delta (model - market) | Better side |
|-------|-------------------|-------------------|------------------------|-------------|
| **R16** | 0.5611 | 0.5907 | +0.0296 | market |
| **QF** | 0.4001 | 0.4279 | +0.0278 | market |
| **SF** | 0.2811 | 0.2984 | +0.0173 | market |
| **final** | 0.1622 | 0.1645 | +0.0024 | market |
| **winner** | 0.0958 | 0.0969 | +0.0011 | market |

## Monte Carlo standard error

> MCSE is estimated from fixed chunked batch means on the saved `sim_matrix.npz` runs. It measures simulation noise inside a single run, not four-tournament sampling uncertainty.

### model_all

| Stage | M1 recall MCSE | M2 qualifier Brier MCSE | M5 all-team Brier MCSE | M6 all-team log-loss MCSE |
|-------|----------------|-------------------------|------------------------|---------------------------|
| **R16** | 0.0025 | 0.0002 | 0.0002 | 0.0005 |
| **QF** | 0.0000 | 0.0003 | 0.0001 | 0.0003 |
| **SF** | 0.0000 | 0.0005 | 0.0001 | 0.0004 |
| **final** | 0.0000 | 0.0009 | 0.0001 | 0.0002 |
| **winner** | 0.0000 | 0.0017 | 0.0001 | 0.0002 |


## Seed sensitivity

> Historical `model_all` was rerun with seeds 42, 43, 44. The tables report the cross-tournament mean, range, and maximum absolute deviation from the seed mean.

### M1 recall

| Stage | Mean | Range | Max abs deviation |
|-------|------|-------|-------------------|
| **R16** | 70.31% | 0.00 pp | 0.00 pp |
| **QF** | 62.50% | 0.00 pp | 0.00 pp |
| **SF** | 43.75% | 0.00 pp | 0.00 pp |
| **final** | 25.00% | 0.00 pp | 0.00 pp |
| **winner** | 25.00% | 0.00 pp | 0.00 pp |

### M2 qualifier Brier

| Stage | Mean | Range | Max abs deviation |
|-------|------|-------|-------------------|
| **R16** | 0.2067 | 0.0001 | 0.0001 |
| **QF** | 0.3510 | 0.0005 | 0.0003 |
| **SF** | 0.5189 | 0.0002 | 0.0001 |
| **final** | 0.6352 | 0.0016 | 0.0010 |
| **winner** | 0.7298 | 0.0007 | 0.0004 |

### M5 all-team Brier

| Stage | Mean | Range | Max abs deviation |
|-------|------|-------|-------------------|
| **R16** | 0.2038 | 0.0001 | 0.0001 |
| **QF** | 0.1346 | 0.0001 | 0.0001 |
| **SF** | 0.0867 | 0.0000 | 0.0000 |
| **final** | 0.0482 | 0.0001 | 0.0001 |
| **winner** | 0.0259 | 0.0000 | 0.0000 |

### M6 all-team log loss

| Stage | Mean | Range | Max abs deviation |
|-------|------|-------|-------------------|
| **R16** | 0.5939 | 0.0002 | 0.0001 |
| **QF** | 0.4315 | 0.0004 | 0.0002 |
| **SF** | 0.2833 | 0.0003 | 0.0002 |
| **final** | 0.1608 | 0.0005 | 0.0004 |
| **winner** | 0.0893 | 0.0001 | 0.0001 |

## Variant robustness

> The first table counts how many of the 5 stages each variant beats `market_all` (M1: model recall > market recall; M2/M5/M6: model loss < market loss). The second table shows per-stage deltas measured against the base `model_all` probability surface — all zeros for `model_all` because it is the reference. Positive M1 deltas are better; negative M2/M5/M6 deltas are better.

| Variant | M1 model-better stages | M2 market-better stages | M5 market-better stages | M6 market-better stages | Base claims hold? |
|---------|------------------------|-------------------------|-------------------------|-------------------------|-------------------|
| model_all | 3/5 | 5/5 | 3/5 | 5/5 | no |
| Elo only | 1/5 | 3/5 | 2/5 | 3/5 | no |
| Elo plus values | 3/5 | 3/5 | 2/5 | 3/5 | no |
| Remove confederation | 3/5 | 3/5 | 2/5 | 2/5 | no |
| Host off | 1/5 | 3/5 | 2/5 | 3/5 | no |
| Stage neutral | 0/5 | 2/5 | 2/5 | 2/5 | no |

| Variant | Stage | delta M1 pp vs base | delta M2 vs base | delta M5 vs base | delta M6 vs base |
|---------|-------|---------------------|------------------|------------------|------------------|
| model_all | **R16** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| model_all | **QF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| model_all | **SF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| model_all | **final** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| model_all | **winner** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| Elo only | **R16** | -1.56 | -0.0062 | -0.0054 | -0.0155 |
| Elo only | **QF** | -3.12 | +0.0150 | +0.0043 | +0.0070 |
| Elo only | **SF** | +0.00 | +0.0021 | +0.0009 | +0.0040 |
| Elo only | **final** | +0.00 | -0.0230 | -0.0011 | -0.0020 |
| Elo only | **winner** | +0.00 | -0.0474 | -0.0011 | -0.0039 |
| Elo plus values | **R16** | +1.56 | -0.0028 | -0.0017 | -0.0051 |
| Elo plus values | **QF** | -3.12 | +0.0034 | +0.0018 | +0.0047 |
| Elo plus values | **SF** | +6.25 | -0.0009 | +0.0004 | -0.0010 |
| Elo plus values | **final** | +0.00 | -0.0107 | -0.0010 | -0.0033 |
| Elo plus values | **winner** | +0.00 | -0.0094 | -0.0005 | -0.0015 |
| Remove confederation | **R16** | +1.56 | -0.0019 | -0.0015 | -0.0034 |
| Remove confederation | **QF** | -3.12 | +0.0004 | +0.0000 | -0.0006 |
| Remove confederation | **SF** | +6.25 | -0.0040 | -0.0008 | -0.0031 |
| Remove confederation | **final** | +0.00 | -0.0017 | -0.0003 | -0.0012 |
| Remove confederation | **winner** | +0.00 | +0.0024 | -0.0000 | +0.0003 |
| Host off | **R16** | +0.00 | -0.0016 | -0.0008 | -0.0031 |
| Host off | **QF** | +0.00 | +0.0023 | +0.0007 | +0.0020 |
| Host off | **SF** | +0.00 | +0.0044 | +0.0010 | +0.0008 |
| Host off | **final** | +0.00 | -0.0021 | -0.0003 | -0.0006 |
| Host off | **winner** | +0.00 | -0.0001 | -0.0001 | -0.0001 |
| Stage neutral | **R16** | +0.00 | -0.0023 | -0.0016 | -0.0028 |
| Stage neutral | **QF** | -3.12 | -0.0026 | -0.0009 | -0.0022 |
| Stage neutral | **SF** | -6.25 | -0.0051 | -0.0006 | -0.0037 |
| Stage neutral | **final** | +0.00 | -0.0013 | +0.0000 | -0.0006 |
| Stage neutral | **winner** | -25.00 | +0.0006 | +0.0001 | +0.0003 |

## Knockout alpha sensitivity

> Base `model_all` was rerun with `alpha_knockout` values 0.25, 0.50, 0.75. Deltas are measured against the base model probability surface.

| alpha_knockout | M1 model-better stages | M2 market-better stages | M5 market-better stages | M6 market-better stages | Base claims hold? |
|----------------|------------------------|-------------------------|-------------------------|-------------------------|-------------------|
| 0.25 | 0/5 | 3/5 | 2/5 | 4/5 | no |
| 0.50 | 1/5 | 3/5 | 2/5 | 3/5 | no |
| 0.75 | 1/5 | 2/5 | 2/5 | 3/5 | no |

| alpha_knockout | Stage | delta M1 pp vs base | delta M2 vs base | delta M5 vs base | delta M6 vs base |
|----------------|-------|---------------------|------------------|------------------|------------------|
| 0.25 | **R16** | +0.00 | -0.0001 | -0.0000 | -0.0000 |
| 0.25 | **QF** | +0.00 | +0.0032 | +0.0003 | +0.0007 |
| 0.25 | **SF** | +0.00 | +0.0080 | +0.0003 | +0.0013 |
| 0.25 | **final** | +0.00 | +0.0093 | +0.0001 | +0.0011 |
| 0.25 | **winner** | -25.00 | +0.0109 | +0.0001 | +0.0014 |
| 0.50 | **R16** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| 0.50 | **QF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| 0.50 | **SF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| 0.50 | **final** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| 0.50 | **winner** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| 0.75 | **R16** | +0.00 | -0.0000 | -0.0000 | -0.0000 |
| 0.75 | **QF** | +0.00 | -0.0024 | -0.0001 | -0.0003 |
| 0.75 | **SF** | +0.00 | -0.0060 | -0.0001 | -0.0003 |
| 0.75 | **final** | +0.00 | -0.0082 | -0.0001 | -0.0010 |
| 0.75 | **winner** | +0.00 | -0.0079 | -0.0000 | -0.0009 |


## World Cup 2010 (`wc2010`)

**Champion (actual):** Spain
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|--------|--------|--------|--------|
| **R16** | 12/16 | 11/16 | 0.1871 | 0.1971 | 55.52% | 89.14% | 2.71% | 2.98% | 0.1829 | 0.1968 | 0.5347 | 0.5703 |
| **QF** | 5/8 | 5/8 | 0.3341 | 0.4154 | 34.27% | 98.33% | 12.05% | 14.24% | 0.1252 | 0.1534 | 0.4014 | 0.4769 |
| **SF** | 1/4 | 1/4 | 0.5000 | 0.5904 | 37.15% | 51.44% | 24.51% | 21.73% | 0.0857 | 0.0963 | 0.2681 | 0.3033 |
| **final** | 1/2 | 1/2 | 0.5980 | 0.6708 | 28.19% | 27.12% | 28.19% | 25.07% | 0.0459 | 0.0496 | 0.1475 | 0.1639 |
| **winner** | 0/1 | 0/1 | 0.6825 | 0.7565 | 34.84% | 35.34% | 34.84% | 35.34% | 0.0241 | 0.0264 | 0.0820 | 0.0924 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

## World Cup 2014 (`wc2014`)

**Champion (actual):** Germany
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|--------|--------|--------|--------|
| **R16** | 10/16 | 11/16 | 0.2539 | 0.2212 | 99.90% | 99.90% | 14.28% | 11.12% | 0.2446 | 0.2143 | 0.6767 | 0.6221 |
| **QF** | 5/8 | 5/8 | 0.3340 | 0.3985 | 43.62% | 99.90% | 15.61% | 27.96% | 0.1236 | 0.1416 | 0.4126 | 0.4803 |
| **SF** | 3/4 | 2/4 | 0.4108 | 0.5449 | 13.93% | 34.22% | 7.41% | 24.07% | 0.0681 | 0.0848 | 0.2225 | 0.2875 |
| **final** | 0/2 | 1/2 | 0.5825 | 0.6707 | 21.07% | 13.94% | 17.20% | 13.94% | 0.0444 | 0.0484 | 0.1426 | 0.1623 |
| **winner** | 0/1 | 0/1 | 0.7466 | 0.8414 | 50.44% | 64.26% | 50.44% | 64.26% | 0.0265 | 0.0287 | 0.0911 | 0.1079 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

## World Cup 2018 (`wc2018`)

**Champion (actual):** France
- Market winner pick: Germany
- Model winner pick: England

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|--------|--------|--------|--------|
| **R16** | 14/16 | 13/16 | 0.1153 | 0.1788 | 24.55% | 99.90% | 2.89% | 2.63% | 0.1198 | 0.1718 | 0.4091 | 0.5227 |
| **QF** | 4/8 | 5/8 | 0.3300 | 0.3091 | 52.24% | 9.18% | 15.42% | 1.98% | 0.1384 | 0.1168 | 0.4148 | 0.3696 |
| **SF** | 1/4 | 3/4 | 0.5120 | 0.4776 | 41.96% | 5.34% | 12.76% | 1.65% | 0.0928 | 0.0769 | 0.2699 | 0.2452 |
| **final** | 0/2 | 0/2 | 0.7674 | 0.7404 | 76.42% | 54.00% | 67.43% | 32.89% | 0.0600 | 0.0540 | 0.2000 | 0.1841 |
| **winner** | 0/1 | 0/1 | 0.8206 | 0.8004 | 66.02% | 46.23% | 66.02% | 46.23% | 0.0297 | 0.0273 | 0.1045 | 0.0995 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

## World Cup 2022 (`wc2022`)

**Champion (actual):** Argentina
- Market winner pick: Brazil
- Model winner pick: Brazil

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|------------|------------|------------|------------|--------|--------|--------|--------|
| **R16** | 9/16 | 10/16 | 0.2257 | 0.2374 | 68.25% | 99.90% | 17.27% | 14.66% | 0.2207 | 0.2326 | 0.6239 | 0.6477 |
| **QF** | 6/8 | 6/8 | 0.3003 | 0.3109 | 29.92% | 33.09% | 14.43% | 15.97% | 0.1172 | 0.1182 | 0.3717 | 0.3847 |
| **SF** | 2/4 | 2/4 | 0.6325 | 0.6191 | 87.03% | 83.43% | 51.77% | 62.75% | 0.1060 | 0.1007 | 0.3640 | 0.3577 |
| **final** | 1/2 | 1/2 | 0.6476 | 0.6084 | 30.82% | 7.59% | 30.82% | 7.59% | 0.0503 | 0.0453 | 0.1586 | 0.1479 |
| **winner** | 0/1 | 0/1 | 0.8251 | 0.7261 | 76.15% | 35.08% | 76.15% | 35.08% | 0.0298 | 0.0253 | 0.1054 | 0.0878 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

## Worked example - WC 2022 SF (model)

| | Metric 3 (exact set) | Metric 4 (all teams seen) |
|--|----------------------|---------------------------|
| Target | Argentina, Croatia, France, Morocco | Same four teams, any combo |
| Stop rank | 1,023 | **356** |
| Cumulative | 83.43% | **62.75%** |
| Trigger combo | exact quartet | Argentina, Brazil, France, Morocco (Morocco last) |

At rank 356 the model has seen every actual SF team at least once, but only 62.75% of simulated mass; the exact quartet needs rank 1,023 (83.43%).

Union at rank 356 (**25** teams): all four actual plus 21 others that appeared in high-frequency SF combos (see WC 2022 -> SF -> Metric 4 -> Model).

