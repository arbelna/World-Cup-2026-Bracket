# Stage prediction backtest

**Generated:** 2026-06-09 10:44 UTC | **Tournaments:** 4 (WC 2010-2022) | **Modes:** `market_all` vs `model_all`

> For the concise human-facing summary, see [`results.md`](../../../results.md). This file keeps the full generated stage-by-stage breakdown.

## How to read this report

| Metric | Source | What it measures |
|--------|--------|------------------|
| **1** | `team_stage_probabilities.csv` | Top *N* teams by `p_at_least_{stage}` vs who really qualified (N: R16=16, QF=8, SF=4, final=2, winner=1) |
| **2** | `team_stage_probabilities.csv` | Mean Brier on teams that actually reached the stage (`p_at_least_{{stage}}` vs outcome 1); lower is better |
| **3** | `analysis/stage_combinations_{{stage}}.csv` | Rank and cumulative probability of the exact actual team set (if never simulated in the run, cumulative is 99.90%) |
| **4** | Same as 3 | Cumulative probability until each actual team has appeared in >=1 combo; lists the union of teams in combos 1..stop rank |
| **5** | `team_stage_probabilities.csv` | All-team binary Brier: mean `(p_at_least_{{stage}} - outcome)^2` across all 32 teams; lower is better |
| **6** | `team_stage_probabilities.csv` | All-team binary log loss: mean cross-entropy across all 32 teams; lower is better |

In tables, `yes` means the condition held, `no` means it did not, and recall is shown as `hits/N`.

---

## Aggregate (average across tournaments)

### M1 top-N recall

| Stage | M1 market | M1 model |
|-------|-----------|-----------|
| **R16** | 70.31% | 70.31% |
| **QF** | 62.50% | 65.62% |
| **SF** | 43.75% | 50.00% |
| **final** | 25.00% | 37.50% |
| **winner** | 0.00% | 0.00% |

### M2 qualifier Brier

| Stage | M2 market | M2 model |
|-------|-----------|----------|
| **R16** | 0.1955 | 0.2086 |
| **QF** | 0.3246 | 0.3585 |
| **SF** | 0.5138 | 0.5580 |
| **final** | 0.6489 | 0.6725 |
| **winner** | 0.7687 | 0.7811 |

### M3 exact-set cumulative

| Stage | M3 cum market | M3 cum model | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 62.05% | 97.21% | +35.16 | market |
| **QF** | 40.01% | 60.13% | +20.11 | market |
| **SF** | 45.02% | 43.61% | -1.41 | model |
| **final** | 39.12% | 25.66% | -13.46 | model |
| **winner** | 56.86% | 45.23% | -11.63 | model |

### M4 all-teams-seen cumulative

| Stage | M4 cum market | M4 cum model | Delta pp (model - market) | Better side |
|-------|---------------|--------------|---------------------------|-------------|
| **R16** | 9.29% | 7.85% | -1.44 | model |
| **QF** | 14.38% | 15.04% | +0.66 | market |
| **SF** | 24.11% | 27.55% | +3.44 | market |
| **final** | 35.91% | 19.87% | -16.03 | model |
| **winner** | 56.86% | 45.23% | -11.63 | model |

### M5 all-team binary Brier

| Stage | M5 market | M5 model | Delta (model - market) | Better side |
|-------|-----------|----------|------------------------|-------------|
| **R16** | 0.1920 | 0.2039 | +0.0119 | market |
| **QF** | 0.1261 | 0.1325 | +0.0064 | market |
| **SF** | 0.0882 | 0.0897 | +0.0015 | market |
| **final** | 0.0502 | 0.0493 | -0.0008 | model |
| **winner** | 0.0275 | 0.0269 | -0.0006 | model |

### M6 all-team binary log loss

| Stage | M6 market | M6 model | Delta (model - market) | Better side |
|-------|-----------|----------|------------------------|-------------|
| **R16** | 0.5611 | 0.5907 | +0.0296 | market |
| **QF** | 0.4001 | 0.4279 | +0.0278 | market |
| **SF** | 0.2811 | 0.2984 | +0.0173 | market |
| **final** | 0.1622 | 0.1645 | +0.0024 | market |
| **winner** | 0.0958 | 0.0969 | +0.0011 | market |

---

## Uncertainty -- bootstrap intervals on model vs market gap

> The bracket backtest aggregates only 4 tournaments. Intervals are a tournament-level block bootstrap (10,000 resamples). A CI spanning 0 means the stage-level gap is not distinguishable from four-tournament noise; the point estimate still indicates direction.

### Recall delta (model minus market)

| Stage | Recall delta (pp) | 95% CI | Tournaments model better | Significant? |
|-------|------------------|--------|--------------------------|--------------|
| **R16** | +0.0 pp | [-6.2, +6.2] | 2 of 4 | no |
| **QF** | +3.1 pp | [+0.0, +9.4] | 1 of 4 | no |
| **SF** | +6.2 pp | [-18.8, +37.5] | 1 of 4 | no |
| **final** | +12.5 pp | [+0.0, +37.5] | 1 of 4 | no |
| **winner** | +0.0 pp | [+0.0, +0.0] | 0 of 4 | no |

### M5 all-team Brier delta (model minus market, lower is better for the winner)

| Stage | Brier delta | 95% CI | Tournaments model better | Significant? |
|-------|------------|--------|--------------------------|--------------|
| **R16** | +0.0119 | [-0.0193, +0.0420] | 3 of 4 | no |
| **QF** | +0.0064 | [-0.0117, +0.0231] | 3 of 4 | no |
| **SF** | +0.0015 | [-0.0106, +0.0137] | 2 of 4 | no |
| **final** | -0.0008 | [-0.0055, +0.0039] | 2 of 4 | no |
| **winner** | -0.0006 | [-0.0034, +0.0022] | 2 of 4 | no |

### M6 all-team log-loss delta (model minus market, lower is better for the winner)

| Stage | Log-loss delta | 95% CI | Tournaments model better | Significant? |
|-------|---------------|--------|--------------------------|--------------|
| **R16** | +0.0296 | [-0.0321, +0.0911] | 3 of 4 | no |
| **QF** | +0.0278 | [-0.0170, +0.0717] | 3 of 4 | no |
| **SF** | +0.0173 | [-0.0155, +0.0501] | 2 of 4 | no |
| **final** | +0.0024 | [-0.0133, +0.0181] | 2 of 4 | no |
| **winner** | +0.0011 | [-0.0113, +0.0136] | 2 of 4 | no |

---

## Monte Carlo standard error

> MCSE is estimated from fixed chunked batch means on the saved `sim_matrix.npz` runs. It measures simulation noise inside a single run, not four-tournament sampling uncertainty.

### market_all

| Stage | M1 recall MCSE | M2 qualifier Brier MCSE | M5 all-team Brier MCSE | M6 all-team log-loss MCSE |
|-------|----------------|-------------------------|------------------------|---------------------------|
| **R16** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **QF** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **SF** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **final** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **winner** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### model_all

| Stage | M1 recall MCSE | M2 qualifier Brier MCSE | M5 all-team Brier MCSE | M6 all-team log-loss MCSE |
|-------|----------------|-------------------------|------------------------|---------------------------|
| **R16** | 0.0025 | 0.0002 | 0.0002 | 0.0005 |
| **QF** | 0.0000 | 0.0003 | 0.0001 | 0.0003 |
| **SF** | 0.0000 | 0.0005 | 0.0001 | 0.0004 |
| **final** | 0.0000 | 0.0009 | 0.0001 | 0.0002 |
| **winner** | 0.0000 | 0.0017 | 0.0001 | 0.0002 |

---

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

> Deltas are measured against the base `model_all` probability surface. Positive M1 deltas are better; negative M2/M5/M6 deltas are better.

| Variant | M1 model-better stages | M2 market-better stages | M5 market-better stages | M6 market-better stages | Base claims hold? |
|---------|------------------------|-------------------------|-------------------------|-------------------------|-------------------|
| Base core7 | 1/5 | 3/5 | 2/5 | 3/5 | no |
| Elo only | 1/5 | 3/5 | 2/5 | 3/5 | no |
| Elo plus values | 3/5 | 3/5 | 2/5 | 3/5 | no |
| Remove confederation | 3/5 | 3/5 | 2/5 | 2/5 | no |
| Host off | 1/5 | 3/5 | 2/5 | 3/5 | no |
| Stage neutral | 0/5 | 2/5 | 2/5 | 2/5 | no |

| Variant | Stage | delta M1 pp vs base | delta M2 vs base | delta M5 vs base | delta M6 vs base |
|---------|-------|---------------------|------------------|------------------|------------------|
| Base core7 | **R16** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| Base core7 | **QF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| Base core7 | **SF** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| Base core7 | **final** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
| Base core7 | **winner** | +0.00 | +0.0000 | +0.0000 | +0.0000 |
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

---

## Calibration -- reliability tables

> Per-stage curves avoid mixing incompatible base rates (R16 ~63% vs Winner ~3%) and keep each reliability diagram interpretable. Pooled ECE is retained below as a secondary summary. Wilson CIs treat each (team, stage, tournament) observation as independent; outcomes within a tournament are correlated due to fixed stage capacity, so the intervals understate true uncertainty.

### Calibration -- market_all

### market_all / R16   (ECE 0.0364)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 8 | 0.066 | 0.000 | [0.000, 0.324] | +0.066 |
| 0.1-0.2 | 12 | 0.147 | 0.167 | [0.047, 0.448] | -0.020 |
| 0.2-0.3 | 16 | 0.244 | 0.312 | [0.142, 0.556] | -0.069 |
| 0.3-0.5 | 36 | 0.417 | 0.444 | [0.295, 0.604] | -0.028 |
| 0.5-0.7 | 21 | 0.599 | 0.571 | [0.365, 0.755] | +0.028 |
| 0.7-0.9 | 23 | 0.828 | 0.783 | [0.581, 0.903] | +0.046 |
| 0.9-1.0 | 12 | 0.931 | 0.917 | [0.646, 0.985] | +0.014 |

### market_all / QF   (ECE 0.0548)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 44 | 0.052 | 0.068 | [0.023, 0.182] | -0.017 |
| 0.1-0.2 | 28 | 0.151 | 0.071 | [0.020, 0.226] | +0.079 |
| 0.2-0.3 | 16 | 0.238 | 0.250 | [0.102, 0.495] | -0.012 |
| 0.3-0.5 | 15 | 0.390 | 0.333 | [0.152, 0.583] | +0.057 |
| 0.5-0.7 | 23 | 0.627 | 0.739 | [0.535, 0.875] | -0.112 |
| 0.7-0.9 | 2 | 0.717 | 0.500 | [0.095, 0.905] | +0.217 |

### market_all / SF   (ECE 0.0347)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 80 | 0.032 | 0.025 | [0.007, 0.087] | +0.007 |
| 0.1-0.2 | 18 | 0.137 | 0.167 | [0.058, 0.392] | -0.030 |
| 0.2-0.3 | 7 | 0.237 | 0.143 | [0.026, 0.513] | +0.094 |
| 0.3-0.5 | 21 | 0.396 | 0.476 | [0.283, 0.676] | -0.080 |
| 0.5-0.7 | 2 | 0.517 | 0.000 | [0.000, 0.658] | +0.517 |

### market_all / final   (ECE 0.0389)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 102 | 0.021 | 0.010 | [0.002, 0.053] | +0.011 |
| 0.1-0.2 | 13 | 0.172 | 0.231 | [0.082, 0.503] | -0.058 |
| 0.2-0.3 | 9 | 0.252 | 0.444 | [0.189, 0.733] | -0.192 |
| 0.3-0.5 | 4 | 0.348 | 0.000 | [0.000, 0.490] | +0.348 |

### market_all / winner   (ECE 0.0112)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 114 | 0.015 | 0.018 | [0.005, 0.062] | -0.003 |
| 0.1-0.2 | 11 | 0.144 | 0.182 | [0.051, 0.477] | -0.038 |
| 0.2-0.3 | 3 | 0.239 | 0.000 | [0.000, 0.562] | +0.239 |

### market_all / pooled (secondary — all stages combined)   (ECE 0.0095)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 348 | 0.026 | 0.023 | [0.012, 0.045] | +0.003 |
| 0.1-0.2 | 82 | 0.150 | 0.146 | [0.086, 0.239] | +0.003 |
| 0.2-0.3 | 51 | 0.242 | 0.275 | [0.171, 0.409] | -0.032 |
| 0.3-0.5 | 76 | 0.402 | 0.408 | [0.304, 0.520] | -0.006 |
| 0.5-0.7 | 46 | 0.610 | 0.630 | [0.486, 0.755] | -0.021 |
| 0.7-0.9 | 25 | 0.819 | 0.760 | [0.566, 0.885] | +0.059 |
| 0.9-1.0 | 12 | 0.931 | 0.917 | [0.646, 0.985] | +0.014 |

### Calibration -- model_all

### model_all / R16   (ECE 0.0640)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 3 | 0.080 | 0.000 | [0.000, 0.562] | +0.080 |
| 0.1-0.2 | 11 | 0.138 | 0.182 | [0.051, 0.477] | -0.044 |
| 0.2-0.3 | 19 | 0.253 | 0.368 | [0.191, 0.590] | -0.116 |
| 0.3-0.5 | 33 | 0.383 | 0.364 | [0.222, 0.534] | +0.019 |
| 0.5-0.7 | 25 | 0.586 | 0.640 | [0.445, 0.798] | -0.054 |
| 0.7-0.9 | 36 | 0.812 | 0.722 | [0.560, 0.842] | +0.090 |
| 0.9-1.0 | 1 | 0.925 | 1.000 | [0.207, 1.000] | -0.075 |

### model_all / QF   (ECE 0.0856)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 37 | 0.059 | 0.081 | [0.028, 0.213] | -0.022 |
| 0.1-0.2 | 29 | 0.146 | 0.069 | [0.019, 0.220] | +0.077 |
| 0.2-0.3 | 17 | 0.239 | 0.176 | [0.062, 0.410] | +0.063 |
| 0.3-0.5 | 23 | 0.399 | 0.304 | [0.156, 0.509] | +0.094 |
| 0.5-0.7 | 22 | 0.561 | 0.773 | [0.566, 0.899] | -0.212 |

### model_all / SF   (ECE 0.0331)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 74 | 0.037 | 0.041 | [0.014, 0.113] | -0.003 |
| 0.1-0.2 | 19 | 0.140 | 0.053 | [0.009, 0.246] | +0.087 |
| 0.2-0.3 | 18 | 0.248 | 0.222 | [0.090, 0.452] | +0.026 |
| 0.3-0.5 | 17 | 0.360 | 0.471 | [0.262, 0.690] | -0.110 |

### model_all / final   (ECE 0.0309)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 96 | 0.024 | 0.010 | [0.002, 0.057] | +0.014 |
| 0.1-0.2 | 23 | 0.151 | 0.174 | [0.070, 0.371] | -0.023 |
| 0.2-0.3 | 7 | 0.223 | 0.429 | [0.158, 0.750] | -0.206 |
| 0.3-0.5 | 2 | 0.315 | 0.000 | [0.000, 0.658] | +0.315 |

### model_all / winner   (ECE 0.0277)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 116 | 0.020 | 0.009 | [0.002, 0.047] | +0.012 |
| 0.1-0.2 | 10 | 0.123 | 0.300 | [0.108, 0.603] | -0.177 |
| 0.2-0.3 | 2 | 0.213 | 0.000 | [0.000, 0.658] | +0.213 |

### model_all / pooled (secondary — all stages combined)   (ECE 0.0242)

| pred bin | n | avg pred | observed | 95% CI (obs) | gap |
|----------|---|----------|----------|--------------|-----|
| 0.0-0.1 | 326 | 0.030 | 0.025 | [0.012, 0.048] | +0.006 |
| 0.1-0.2 | 92 | 0.142 | 0.130 | [0.076, 0.214] | +0.012 |
| 0.2-0.3 | 63 | 0.243 | 0.270 | [0.176, 0.390] | -0.027 |
| 0.3-0.5 | 75 | 0.381 | 0.360 | [0.261, 0.473] | +0.021 |
| 0.5-0.7 | 47 | 0.574 | 0.702 | [0.560, 0.813] | -0.128 |
| 0.7-0.9 | 36 | 0.812 | 0.722 | [0.560, 0.842] | +0.090 |
| 0.9-1.0 | 1 | 0.925 | 1.000 | [0.207, 1.000] | -0.075 |

---

## World Cup 2010 (`wc2010`)

**Champion (actual):** Spain

### At a glance

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|----------|----------|----------|----------|--------|--------|--------|--------|
| **R16** | 12/16 | 11/16 | 0.1871 | 0.1971 | 55.52% | 89.14% | 2.71% | 2.98% | 0.1829 | 0.1968 | 0.5347 | 0.5703 |
| **QF** | 5/8 | 5/8 | 0.3341 | 0.4154 | 34.27% | 98.33% | 12.05% | 14.24% | 0.1252 | 0.1534 | 0.4014 | 0.4769 |
| **SF** | 1/4 | 1/4 | 0.5000 | 0.5904 | 37.15% | 51.44% | 24.51% | 21.73% | 0.0857 | 0.0963 | 0.2681 | 0.3033 |
| **final** | 1/2 | 1/2 | 0.5980 | 0.6708 | 28.19% | 27.12% | 28.19% | 25.07% | 0.0459 | 0.0496 | 0.1475 | 0.1639 |
| **winner** | 0/1 | 0/1 | 0.6825 | 0.7565 | 34.84% | 35.34% | 34.84% | 35.34% | 0.0241 | 0.0264 | 0.0820 | 0.0924 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

### R16

**Actual participants (16)** - 16 teams
> Argentina | Brazil | Chile | England | Germany | Ghana
> Japan | Mexico | Netherlands | Paraguay | Portugal | Slovakia
> South Korea | Spain | United States | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **12/16** | **11/16** |
| Perfect set | no | no |
| Missed | Ghana, Japan, Slovakia, South Korea | |
| | | Ghana, Japan, Paraguay, South Korea, United States |

**Market top-16 pick** - 16 teams
> Spain | England | Argentina | Germany | Netherlands | Italy
> Brazil | Portugal | Paraguay | France | Serbia | Chile
> United States | Uruguay | Mexico | Ivory Coast

**Model top-16 pick** - 16 teams
> Brazil | Spain | England | Argentina | Italy | Netherlands
> Germany | Serbia | France | Portugal | Mexico | Slovakia
> Chile | Slovenia | Cameroon | Uruguay

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.1871 | 0.1971 |
| Avg p on qualifiers | 63.43% | 61.41% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Brazil, Chile, England, Germany, Ghana, Japan, Mexico, Netherlands, Paraguay, Portugal, Slovakia, South Korea, Spain, United States, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | 6,758 / 60,708 | 56,847 / 78,558 |
| p(actual set) | 0.00% | 0.00% |
| Cumulative through that rank | 55.52% | 89.14% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **40** |
| Cumulative probability | **2.71%** |
| Last actual team to appear | **Ghana** |
| Combo at that rank | Argentina, Brazil, Chile, Denmark, England, France, Germany, Ghana, Italy, Netherlands, Nigeria, Paraguay, Portugal, Spain, United States, Uruguay |
| Union size (teams in ranks 1-40) | 27 |

**Actual teams covered** - 16 teams
> Argentina | Brazil | Chile | England | Germany | Ghana
> Japan | Mexico | Netherlands | Paraguay | Portugal | Slovakia
> South Korea | Spain | United States | Uruguay

**Other teams in union (not in actual set)** - 11 teams
> Cameroon | Denmark | France | Greece | Italy | Ivory Coast
> Nigeria | Serbia | Slovenia | South Africa | Switzerland

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **37** |
| Cumulative probability | **2.98%** |
| Last actual team to appear | **Ghana** |
| Combo at that rank | Argentina, Brazil, Cameroon, Chile, England, France, Germany, Ghana, Greece, Italy, Mexico, Netherlands, Portugal, Slovakia, Slovenia, Spain |
| Union size (teams in ranks 1-37) | 28 |

**Actual teams covered** - 16 teams
> Argentina | Brazil | Chile | England | Germany | Ghana
> Japan | Mexico | Netherlands | Paraguay | Portugal | Slovakia
> South Korea | Spain | United States | Uruguay

**Other teams in union (not in actual set)** - 12 teams
> Algeria | Cameroon | Denmark | France | Greece | Honduras
> Italy | Ivory Coast | Nigeria | Serbia | Slovenia | Switzerland

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1829 | 0.1968 |
| Delta (model - market) | | +0.0140 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.5347 | 0.5703 |
| Delta (model - market) | | +0.0356 (market wins) |

### QF

**Actual participants (8)** - 8 teams
> Argentina | Brazil | Germany | Ghana | Netherlands | Paraguay
> Spain | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **5/8** | **5/8** |
| Perfect set | no | no |
| Missed | Ghana, Paraguay, Uruguay | |
| | | Ghana, Paraguay, Uruguay |

**Market top-8 pick** - 8 teams
> England | Argentina | Netherlands | Germany | Spain | Brazil
> Italy | France

**Model top-8 pick** - 8 teams
> Brazil | England | Argentina | Italy | Spain | Netherlands
> Germany | France

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.3341 | 0.4154 |
| Avg p on qualifiers | 46.14% | 38.67% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Brazil, Germany, Ghana, Netherlands, Paraguay, Spain, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | 1,140 / 46,322 | 56,842 / 60,175 |
| p(actual set) | 0.01% | 0.00% |
| Cumulative through that rank | 34.27% | 98.33% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **147** |
| Cumulative probability | **12.05%** |
| Last actual team to appear | **Ghana** |
| Combo at that rank | Argentina, Brazil, France, Germany, Ghana, Italy, Netherlands, Spain |
| Union size (teams in ranks 1-147) | 27 |

**Actual teams covered** - 8 teams
> Argentina | Brazil | Germany | Ghana | Netherlands | Paraguay
> Spain | Uruguay

**Other teams in union (not in actual set)** - 19 teams
> Cameroon | Chile | Denmark | England | France | Greece
> Italy | Ivory Coast | Japan | Mexico | Nigeria | Portugal
> Serbia | Slovakia | Slovenia | South Africa | South Korea | Switzerland
> United States

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **390** |
| Cumulative probability | **14.24%** |
| Last actual team to appear | **Ghana** |
| Combo at that rank | Argentina, Brazil, France, Germany, Ghana, Italy, Netherlands, Spain |
| Union size (teams in ranks 1-390) | 25 |

**Actual teams covered** - 8 teams
> Argentina | Brazil | Germany | Ghana | Netherlands | Paraguay
> Spain | Uruguay

**Other teams in union (not in actual set)** - 17 teams
> Algeria | Cameroon | Chile | England | France | Greece
> Italy | Ivory Coast | Japan | Mexico | Nigeria | Portugal
> Serbia | Slovakia | Slovenia | South Korea | United States

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1252 | 0.1534 |
| Delta (model - market) | | +0.0282 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.4014 | 0.4769 |
| Delta (model - market) | | +0.0756 (market wins) |

### SF

**Actual participants (4)** - 4 teams
> Germany | Netherlands | Spain | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **1/4** | **1/4** |
| Perfect set | no | no |
| Missed | Germany, Netherlands, Uruguay | |
| | | Germany, Netherlands, Uruguay |

**Market top-4 pick** - 4 teams
> Spain | England | Brazil | Argentina

**Model top-4 pick** - 4 teams
> Brazil | Spain | England | Argentina

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.5000 | 0.5904 |
| Avg p on qualifiers | 30.48% | 23.72% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Germany, Netherlands, Spain, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | 78 / 6,180 | 336 / 7,805 |
| p(actual set) | 0.21% | 0.06% |
| Cumulative through that rank | 37.15% | 51.44% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **32** |
| Cumulative probability | **24.51%** |
| Last actual team to appear | **Uruguay** |
| Combo at that rank | Argentina, Brazil, Spain, Uruguay |
| Union size (teams in ranks 1-32) | 13 |

**Actual teams covered** - 4 teams
> Germany | Netherlands | Spain | Uruguay

**Other teams in union (not in actual set)** - 9 teams
> Argentina | Brazil | Chile | England | France | Italy
> Ivory Coast | Portugal | Serbia

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **64** |
| Cumulative probability | **21.73%** |
| Last actual team to appear | **Uruguay** |
| Combo at that rank | Brazil, England, Spain, Uruguay |
| Union size (teams in ranks 1-64) | 16 |

**Actual teams covered** - 4 teams
> Germany | Netherlands | Spain | Uruguay

**Other teams in union (not in actual set)** - 12 teams
> Argentina | Brazil | Chile | England | France | Greece
> Italy | Mexico | Portugal | Serbia | Slovakia | Slovenia

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0857 | 0.0963 |
| Delta (model - market) | | +0.0106 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.2681 | 0.3033 |
| Delta (model - market) | | +0.0352 (market wins) |

### final

**Actual participants (2)** - 2 teams
> Netherlands | Spain

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **1/2** | **1/2** |
| Perfect set | no | no |
| Missed | Netherlands | |
| | | Netherlands |

**Market top-2 pick** - 2 teams
> Brazil | Spain

**Model top-2 pick** - 2 teams
> Brazil | Spain

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.5980 | 0.6708 |
| Avg p on qualifiers | 22.89% | 18.21% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Netherlands, Spain

| | Market | Model |
|--|--------|-------|
| Rank | 6 / 428 | 9 / 461 |
| p(actual set) | 3.58% | 2.04% |
| Cumulative through that rank | 28.19% | 27.12% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **6** |
| Cumulative probability | **28.19%** |
| Last actual team to appear | **Netherlands** |
| Combo at that rank | Netherlands, Spain |
| Union size (teams in ranks 1-6) | 6 |

**Actual teams covered** - 2 teams
> Netherlands | Spain

**Other teams in union (not in actual set)** - 4 teams
> Argentina | Brazil | England | Germany

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **8** |
| Cumulative probability | **25.07%** |
| Last actual team to appear | **Netherlands** |
| Combo at that rank | Brazil, Netherlands |
| Union size (teams in ranks 1-8) | 8 |

**Actual teams covered** - 2 teams
> Netherlands | Spain

**Other teams in union (not in actual set)** - 6 teams
> Argentina | Brazil | England | Germany | Italy | Portugal

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0459 | 0.0496 |
| Delta (model - market) | | +0.0038 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.1475 | 0.1639 |
| Delta (model - market) | | +0.0164 (market wins) |

### winner

**Actual participants (1)** - 1 teams
> Spain

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/1** | **0/1** |
| Perfect set | no | no |
| Missed | Spain | |
| | | Spain |

**Market top-1 pick** - 1 teams
> Brazil

**Model top-1 pick** - 1 teams
> Brazil

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.6825 | 0.7565 |
| Avg p on qualifiers | 17.39% | 13.02% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Spain

| | Market | Model |
|--|--------|-------|
| Rank | 2 / 31 | 2 / 32 |
| p(actual set) | 17.39% | 13.02% |
| Cumulative through that rank | 34.84% | 35.34% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **2** |
| Cumulative probability | **34.84%** |
| Last actual team to appear | **Spain** |
| Combo at that rank | Spain |
| Union size (teams in ranks 1-2) | 2 |

**Actual teams covered** - 1 teams
> Spain

**Other teams in union (not in actual set)** - 1 teams
> Brazil

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **2** |
| Cumulative probability | **35.34%** |
| Last actual team to appear | **Spain** |
| Combo at that rank | Spain |
| Union size (teams in ranks 1-2) | 2 |

**Actual teams covered** - 1 teams
> Spain

**Other teams in union (not in actual set)** - 1 teams
> Brazil

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0241 | 0.0264 |
| Delta (model - market) | | +0.0022 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.0820 | 0.0924 |
| Delta (model - market) | | +0.0104 (market wins) |

---

## World Cup 2014 (`wc2014`)

**Champion (actual):** Germany

### At a glance

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|----------|----------|----------|----------|--------|--------|--------|--------|
| **R16** | 10/16 | 11/16 | 0.2539 | 0.2212 | 99.90% | 99.90% | 14.28% | 11.12% | 0.2446 | 0.2143 | 0.6767 | 0.6221 |
| **QF** | 5/8 | 5/8 | 0.3340 | 0.3985 | 43.62% | 99.90% | 15.61% | 27.96% | 0.1236 | 0.1416 | 0.4126 | 0.4803 |
| **SF** | 3/4 | 2/4 | 0.4108 | 0.5449 | 13.93% | 34.22% | 7.41% | 24.07% | 0.0681 | 0.0848 | 0.2225 | 0.2875 |
| **final** | 0/2 | 1/2 | 0.5825 | 0.6707 | 21.07% | 13.94% | 17.20% | 13.94% | 0.0444 | 0.0484 | 0.1426 | 0.1623 |
| **winner** | 0/1 | 0/1 | 0.7466 | 0.8414 | 50.44% | 64.26% | 50.44% | 64.26% | 0.0265 | 0.0287 | 0.0911 | 0.1079 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

### R16

**Actual participants (16)** - 16 teams
> Algeria | Argentina | Belgium | Brazil | Chile | Colombia
> Costa Rica | France | Germany | Greece | Mexico | Netherlands
> Nigeria | Switzerland | United States | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **10/16** | **11/16** |
| Perfect set | no | no |
| Missed | Algeria, Costa Rica, Greece, Mexico, Nigeria, United States | |
| | | Algeria, Costa Rica, Greece, Netherlands, United States |

**Market top-16 pick** - 16 teams
> Brazil | Argentina | France | Germany | Spain | Belgium
> Colombia | England | Portugal | Russia | Italy | Switzerland
> Netherlands | Uruguay | Chile | Ivory Coast

**Model top-16 pick** - 16 teams
> Argentina | Brazil | France | Belgium | Spain | Germany
> Uruguay | Russia | Chile | Colombia | England | Switzerland
> Italy | Ivory Coast | Nigeria | Mexico

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.2539 | 0.2212 |
| Avg p on qualifiers | 56.94% | 58.70% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Algeria, Argentina, Belgium, Brazil, Chile, Colombia, Costa Rica, France, Germany, Greece, Mexico, Netherlands, Nigeria, Switzerland, United States, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | not observed / 66,269 | not observed / 92,594 |
| p(actual set) | 0.00% | 0.00% |
| Cumulative through that rank | 99.90% | 99.90% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **488** |
| Cumulative probability | **14.28%** |
| Last actual team to appear | **Costa Rica** |
| Combo at that rank | Argentina, Belgium, Bosnia and Herzegovina, Brazil, Colombia, Costa Rica, Croatia, France, Germany, Ivory Coast, Netherlands, Portugal, Russia, Spain, Switzerland, Uruguay |
| Union size (teams in ranks 1-488) | 30 |

**Actual teams covered** - 16 teams
> Algeria | Argentina | Belgium | Brazil | Chile | Colombia
> Costa Rica | France | Germany | Greece | Mexico | Netherlands
> Nigeria | Switzerland | United States | Uruguay

**Other teams in union (not in actual set)** - 14 teams
> Bosnia and Herzegovina | Cameroon | Croatia | Ecuador | England | Ghana
> Iran | Italy | Ivory Coast | Japan | Portugal | Russia
> South Korea | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **698** |
| Cumulative probability | **11.12%** |
| Last actual team to appear | **Costa Rica** |
| Combo at that rank | Argentina, Belgium, Brazil, Chile, Colombia, Costa Rica, Ecuador, France, Germany, Ivory Coast, Mexico, Nigeria, Portugal, Russia, Spain, Uruguay |
| Union size (teams in ranks 1-698) | 32 |

**Actual teams covered** - 16 teams
> Algeria | Argentina | Belgium | Brazil | Chile | Colombia
> Costa Rica | France | Germany | Greece | Mexico | Netherlands
> Nigeria | Switzerland | United States | Uruguay

**Other teams in union (not in actual set)** - 16 teams
> Australia | Bosnia and Herzegovina | Cameroon | Croatia | Ecuador | England
> Ghana | Honduras | Iran | Italy | Ivory Coast | Japan
> Portugal | Russia | South Korea | Spain

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.2446 | 0.2143 |
| Delta (model - market) | | -0.0304 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.6767 | 0.6221 |
| Delta (model - market) | | -0.0546 (model wins) |

### QF

**Actual participants (8)** - 8 teams
> Argentina | Belgium | Brazil | Colombia | Costa Rica | France
> Germany | Netherlands

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **5/8** | **5/8** |
| Perfect set | no | no |
| Missed | Belgium, Costa Rica, Netherlands | |
| | | Colombia, Costa Rica, Netherlands |

**Market top-8 pick** - 8 teams
> Argentina | Germany | Brazil | France | Spain | England
> Portugal | Colombia

**Model top-8 pick** - 8 teams
> Argentina | Brazil | France | Belgium | Germany | Spain
> Uruguay | England

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.3340 | 0.3985 |
| Avg p on qualifiers | 46.03% | 39.94% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Belgium, Brazil, Colombia, Costa Rica, France, Germany, Netherlands

| | Market | Model |
|--|--------|-------|
| Rank | 2,300 / 49,064 | not observed / 71,275 |
| p(actual set) | 0.01% | 0.00% |
| Cumulative through that rank | 43.62% | 99.90% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **255** |
| Cumulative probability | **15.61%** |
| Last actual team to appear | **Costa Rica** |
| Combo at that rank | Argentina, Brazil, Costa Rica, England, France, Germany, Portugal, Spain |
| Union size (teams in ranks 1-255) | 26 |

**Actual teams covered** - 8 teams
> Argentina | Belgium | Brazil | Colombia | Costa Rica | France
> Germany | Netherlands

**Other teams in union (not in actual set)** - 18 teams
> Bosnia and Herzegovina | Chile | Croatia | Ecuador | England | Ghana
> Greece | Italy | Ivory Coast | Japan | Mexico | Nigeria
> Portugal | Russia | Spain | Switzerland | United States | Uruguay

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **2348** |
| Cumulative probability | **27.96%** |
| Last actual team to appear | **Costa Rica** |
| Combo at that rank | Argentina, Belgium, Chile, Costa Rica, France, Russia, Spain, Uruguay |
| Union size (teams in ranks 1-2348) | 30 |

**Actual teams covered** - 8 teams
> Argentina | Belgium | Brazil | Colombia | Costa Rica | France
> Germany | Netherlands

**Other teams in union (not in actual set)** - 22 teams
> Algeria | Bosnia and Herzegovina | Cameroon | Chile | Croatia | Ecuador
> England | Ghana | Greece | Iran | Italy | Ivory Coast
> Japan | Mexico | Nigeria | Portugal | Russia | South Korea
> Spain | Switzerland | United States | Uruguay

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1236 | 0.1416 |
| Delta (model - market) | | +0.0180 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.4126 | 0.4803 |
| Delta (model - market) | | +0.0678 (market wins) |

### SF

**Actual participants (4)** - 4 teams
> Argentina | Brazil | Germany | Netherlands

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **3/4** | **2/4** |
| Perfect set | no | no |
| Missed | Netherlands | |
| | | Germany, Netherlands |

**Market top-4 pick** - 4 teams
> Brazil | Spain | Argentina | Germany

**Model top-4 pick** - 4 teams
> Brazil | Argentina | France | Belgium

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.4108 | 0.5449 |
| Avg p on qualifiers | 36.95% | 27.30% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Brazil, Germany, Netherlands

| | Market | Model |
|--|--------|-------|
| Rank | 15 / 6,573 | 217 / 8,924 |
| p(actual set) | 0.53% | 0.08% |
| Cumulative through that rank | 13.93% | 34.22% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **5** |
| Cumulative probability | **7.41%** |
| Last actual team to appear | **Netherlands** |
| Combo at that rank | Argentina, France, Netherlands, Spain |
| Union size (teams in ranks 1-5) | 7 |

**Actual teams covered** - 4 teams
> Argentina | Brazil | Germany | Netherlands

**Other teams in union (not in actual set)** - 3 teams
> France | Portugal | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **115** |
| Cumulative probability | **24.07%** |
| Last actual team to appear | **Netherlands** |
| Combo at that rank | Argentina, Brazil, France, Netherlands |
| Union size (teams in ranks 1-115) | 21 |

**Actual teams covered** - 4 teams
> Argentina | Brazil | Germany | Netherlands

**Other teams in union (not in actual set)** - 17 teams
> Belgium | Chile | Colombia | Ecuador | England | France
> Italy | Ivory Coast | Japan | Mexico | Nigeria | Portugal
> Russia | Spain | Switzerland | United States | Uruguay

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0681 | 0.0848 |
| Delta (model - market) | | +0.0167 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.2225 | 0.2875 |
| Delta (model - market) | | +0.0650 (market wins) |

### final

**Actual participants (2)** - 2 teams
> Argentina | Germany

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/2** | **1/2** |
| Perfect set | no | no |
| Missed | Argentina, Germany | |
| | | Germany |

**Market top-2 pick** - 2 teams
> Brazil | Spain

**Model top-2 pick** - 2 teams
> Brazil | Argentina

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.5825 | 0.6707 |
| Avg p on qualifiers | 23.68% | 18.16% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Germany

| | Market | Model |
|--|--------|-------|
| Rank | 4 / 447 | 5 / 474 |
| p(actual set) | 3.87% | 2.08% |
| Cumulative through that rank | 21.07% | 13.94% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **3** |
| Cumulative probability | **17.20%** |
| Last actual team to appear | **Germany** |
| Combo at that rank | Germany, Spain |
| Union size (teams in ranks 1-3) | 4 |

**Actual teams covered** - 2 teams
> Argentina | Germany

**Other teams in union (not in actual set)** - 2 teams
> Brazil | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **5** |
| Cumulative probability | **13.94%** |
| Last actual team to appear | **Germany** |
| Combo at that rank | Argentina, Germany |
| Union size (teams in ranks 1-5) | 6 |

**Actual teams covered** - 2 teams
> Argentina | Germany

**Other teams in union (not in actual set)** - 4 teams
> Belgium | Brazil | France | Spain

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0444 | 0.0484 |
| Delta (model - market) | | +0.0040 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.1426 | 0.1623 |
| Delta (model - market) | | +0.0197 (market wins) |

### winner

**Actual participants (1)** - 1 teams
> Germany

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/1** | **0/1** |
| Perfect set | no | no |
| Missed | Germany | |
| | | Germany |

**Market top-1 pick** - 1 teams
> Brazil

**Model top-1 pick** - 1 teams
> Brazil

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.7466 | 0.8414 |
| Avg p on qualifiers | 13.59% | 8.27% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Germany

| | Market | Model |
|--|--------|-------|
| Rank | 3 / 32 | 6 / 32 |
| p(actual set) | 13.59% | 8.27% |
| Cumulative through that rank | 50.44% | 64.26% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **3** |
| Cumulative probability | **50.44%** |
| Last actual team to appear | **Germany** |
| Combo at that rank | Germany |
| Union size (teams in ranks 1-3) | 3 |

**Actual teams covered** - 1 teams
> Germany

**Other teams in union (not in actual set)** - 2 teams
> Brazil | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **6** |
| Cumulative probability | **64.26%** |
| Last actual team to appear | **Germany** |
| Combo at that rank | Germany |
| Union size (teams in ranks 1-6) | 6 |

**Actual teams covered** - 1 teams
> Germany

**Other teams in union (not in actual set)** - 5 teams
> Argentina | Belgium | Brazil | France | Spain

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0265 | 0.0287 |
| Delta (model - market) | | +0.0023 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.0911 | 0.1079 |
| Delta (model - market) | | +0.0167 (market wins) |

---

## World Cup 2018 (`wc2018`)

**Champion (actual):** France

### At a glance

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|----------|----------|----------|----------|--------|--------|--------|--------|
| **R16** | 14/16 | 13/16 | 0.1153 | 0.1788 | 24.55% | 99.90% | 2.89% | 2.63% | 0.1198 | 0.1718 | 0.4091 | 0.5227 |
| **QF** | 4/8 | 5/8 | 0.3300 | 0.3091 | 52.24% | 9.18% | 15.42% | 1.98% | 0.1384 | 0.1168 | 0.4148 | 0.3696 |
| **SF** | 1/4 | 3/4 | 0.5120 | 0.4776 | 41.96% | 5.34% | 12.76% | 1.65% | 0.0928 | 0.0769 | 0.2699 | 0.2452 |
| **final** | 0/2 | 0/2 | 0.7674 | 0.7404 | 76.42% | 54.00% | 67.43% | 32.89% | 0.0600 | 0.0540 | 0.2000 | 0.1841 |
| **winner** | 0/1 | 0/1 | 0.8206 | 0.8004 | 66.02% | 46.23% | 66.02% | 46.23% | 0.0297 | 0.0273 | 0.1045 | 0.0995 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

### R16

**Actual participants (16)** - 16 teams
> Argentina | Belgium | Brazil | Colombia | Croatia | Denmark
> England | France | Japan | Mexico | Portugal | Russia
> Spain | Sweden | Switzerland | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **14/16** | **13/16** |
| Perfect set | no | no |
| Missed | Japan, Sweden | |
| | | Japan, Mexico, Switzerland |

**Market top-16 pick** - 16 teams
> Germany | Brazil | Spain | Belgium | France | Uruguay
> Argentina | England | Colombia | Russia | Portugal | Croatia
> Denmark | Mexico | Poland | Switzerland

**Model top-16 pick** - 16 teams
> Brazil | France | England | Belgium | Germany | Argentina
> Uruguay | Colombia | Spain | Croatia | Russia | Poland
> Serbia | Sweden | Portugal | Denmark

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.1153 | 0.1788 |
| Avg p on qualifiers | 71.74% | 63.43% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Belgium, Brazil, Colombia, Croatia, Denmark, England, France, Japan, Mexico, Portugal, Russia, Spain, Sweden, Switzerland, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | 293 / 45,685 | not observed / 88,352 |
| p(actual set) | 0.04% | 0.00% |
| Cumulative through that rank | 24.55% | 99.90% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **7** |
| Cumulative probability | **2.89%** |
| Last actual team to appear | **Sweden** |
| Combo at that rank | Argentina, Belgium, Brazil, Colombia, Croatia, Denmark, England, France, Germany, Poland, Portugal, Russia, Spain, Sweden, Switzerland, Uruguay |
| Union size (teams in ranks 1-7) | 20 |

**Actual teams covered** - 16 teams
> Argentina | Belgium | Brazil | Colombia | Croatia | Denmark
> England | France | Japan | Mexico | Portugal | Russia
> Spain | Sweden | Switzerland | Uruguay

**Other teams in union (not in actual set)** - 4 teams
> Germany | Poland | Senegal | Serbia

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **47** |
| Cumulative probability | **2.63%** |
| Last actual team to appear | **Japan** |
| Combo at that rank | Argentina, Belgium, Brazil, Colombia, Croatia, England, France, Germany, Japan, Peru, Portugal, Russia, Serbia, Spain, Sweden, Uruguay |
| Union size (teams in ranks 1-47) | 28 |

**Actual teams covered** - 16 teams
> Argentina | Belgium | Brazil | Colombia | Croatia | Denmark
> England | France | Japan | Mexico | Portugal | Russia
> Spain | Sweden | Switzerland | Uruguay

**Other teams in union (not in actual set)** - 12 teams
> Australia | Costa Rica | Egypt | Germany | Iran | Morocco
> Nigeria | Peru | Poland | Senegal | Serbia | South Korea

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1198 | 0.1718 |
| Delta (model - market) | | +0.0520 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.4091 | 0.5227 |
| Delta (model - market) | | +0.1136 (market wins) |

### QF

**Actual participants (8)** - 8 teams
> Belgium | Brazil | Croatia | England | France | Russia
> Sweden | Uruguay

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **4/8** | **5/8** |
| Perfect set | no | no |
| Missed | Croatia, Russia, Sweden, Uruguay | |
| | | Croatia, Russia, Sweden |

**Market top-8 pick** - 8 teams
> Spain | Germany | Belgium | Brazil | England | France
> Argentina | Portugal

**Model top-8 pick** - 8 teams
> England | Brazil | Belgium | France | Argentina | Germany
> Uruguay | Spain

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.3300 | 0.3091 |
| Avg p on qualifiers | 46.30% | 45.89% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Belgium, Brazil, Croatia, England, France, Russia, Sweden, Uruguay

| | Market | Model |
|--|--------|-------|
| Rank | 1,099 / 32,881 | 177 / 64,976 |
| p(actual set) | 0.01% | 0.03% |
| Cumulative through that rank | 52.24% | 9.18% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **49** |
| Cumulative probability | **15.42%** |
| Last actual team to appear | **Sweden** |
| Combo at that rank | Argentina, Belgium, England, France, Germany, Portugal, Spain, Sweden |
| Union size (teams in ranks 1-49) | 19 |

**Actual teams covered** - 8 teams
> Belgium | Brazil | Croatia | England | France | Russia
> Sweden | Uruguay

**Other teams in union (not in actual set)** - 11 teams
> Argentina | Colombia | Denmark | Germany | Mexico | Morocco
> Peru | Portugal | Serbia | Spain | Switzerland

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **16** |
| Cumulative probability | **1.98%** |
| Last actual team to appear | **Sweden** |
| Combo at that rank | Argentina, Belgium, England, France, Germany, Spain, Sweden, Uruguay |
| Union size (teams in ranks 1-16) | 13 |

**Actual teams covered** - 8 teams
> Belgium | Brazil | Croatia | England | France | Russia
> Sweden | Uruguay

**Other teams in union (not in actual set)** - 5 teams
> Argentina | Germany | Portugal | Serbia | Spain

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1384 | 0.1168 |
| Delta (model - market) | | -0.0216 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.4148 | 0.3696 |
| Delta (model - market) | | -0.0452 (model wins) |

### SF

**Actual participants (4)** - 4 teams
> Belgium | Croatia | England | France

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **1/4** | **3/4** |
| Perfect set | no | no |
| Missed | Belgium, Croatia, England | |
| | | Croatia |

**Market top-4 pick** - 4 teams
> Germany | Brazil | Spain | France

**Model top-4 pick** - 4 teams
> England | Belgium | France | Argentina

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.5120 | 0.4776 |
| Avg p on qualifiers | 28.82% | 31.16% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Belgium, Croatia, England, France

| | Market | Model |
|--|--------|-------|
| Rank | 64 / 5,029 | 9 / 8,605 |
| p(actual set) | 0.30% | 0.47% |
| Cumulative through that rank | 41.96% | 5.34% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **8** |
| Cumulative probability | **12.76%** |
| Last actual team to appear | **England** |
| Combo at that rank | Belgium, England, France, Spain |
| Union size (teams in ranks 1-8) | 10 |

**Actual teams covered** - 4 teams
> Belgium | Croatia | England | France

**Other teams in union (not in actual set)** - 6 teams
> Argentina | Brazil | Germany | Portugal | Spain | Uruguay

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **2** |
| Cumulative probability | **1.65%** |
| Last actual team to appear | **Croatia** |
| Combo at that rank | Argentina, Belgium, Croatia, England |
| Union size (teams in ranks 1-2) | 5 |

**Actual teams covered** - 4 teams
> Belgium | Croatia | England | France

**Other teams in union (not in actual set)** - 1 teams
> Argentina

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0928 | 0.0769 |
| Delta (model - market) | | -0.0159 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.2699 | 0.2452 |
| Delta (model - market) | | -0.0247 (model wins) |

### final

**Actual participants (2)** - 2 teams
> Croatia | France

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/2** | **0/2** |
| Perfect set | no | no |
| Missed | Croatia, France | |
| | | Croatia, France |

**Market top-2 pick** - 2 teams
> Germany | Brazil

**Model top-2 pick** - 2 teams
> England | Belgium

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.7674 | 0.7404 |
| Avg p on qualifiers | 12.61% | 14.08% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Croatia, France

| | Market | Model |
|--|--------|-------|
| Rank | 34 / 398 | 32 / 484 |
| p(actual set) | 0.63% | 1.01% |
| Cumulative through that rank | 76.42% | 54.00% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **24** |
| Cumulative probability | **67.43%** |
| Last actual team to appear | **Croatia** |
| Combo at that rank | Croatia, Germany |
| Union size (teams in ranks 1-24) | 10 |

**Actual teams covered** - 2 teams
> Croatia | France

**Other teams in union (not in actual set)** - 8 teams
> Argentina | Belgium | Brazil | England | Germany | Portugal
> Spain | Uruguay

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **15** |
| Cumulative probability | **32.89%** |
| Last actual team to appear | **Croatia** |
| Combo at that rank | Argentina, Croatia |
| Union size (teams in ranks 1-15) | 7 |

**Actual teams covered** - 2 teams
> Croatia | France

**Other teams in union (not in actual set)** - 5 teams
> Argentina | Belgium | Brazil | England | Germany

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0600 | 0.0540 |
| Delta (model - market) | | -0.0061 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.2000 | 0.1841 |
| Delta (model - market) | | -0.0159 (model wins) |

### winner

**Actual participants (1)** - 1 teams
> France

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/1** | **0/1** |
| Perfect set | no | no |
| Missed | France | |
| | | France |

**Market top-1 pick** - 1 teams
> Germany

**Model top-1 pick** - 1 teams
> England

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.8206 | 0.8004 |
| Avg p on qualifiers | 9.41% | 10.54% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: France

| | Market | Model |
|--|--------|-------|
| Rank | 4 / 31 | 4 / 32 |
| p(actual set) | 9.41% | 10.54% |
| Cumulative through that rank | 66.02% | 46.23% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **4** |
| Cumulative probability | **66.02%** |
| Last actual team to appear | **France** |
| Combo at that rank | France |
| Union size (teams in ranks 1-4) | 4 |

**Actual teams covered** - 1 teams
> France

**Other teams in union (not in actual set)** - 3 teams
> Brazil | Germany | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **4** |
| Cumulative probability | **46.23%** |
| Last actual team to appear | **France** |
| Combo at that rank | France |
| Union size (teams in ranks 1-4) | 4 |

**Actual teams covered** - 1 teams
> France

**Other teams in union (not in actual set)** - 3 teams
> Belgium | Brazil | England

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0297 | 0.0273 |
| Delta (model - market) | | -0.0023 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.1045 | 0.0995 |
| Delta (model - market) | | -0.0049 (model wins) |

---

## World Cup 2022 (`wc2022`)

**Champion (actual):** Argentina

### At a glance

| Stage | M1 market | M1 model | M2 mkt | M2 mdl | M3 cum mkt | M3 cum mdl | M4 cum mkt | M4 cum mdl | M5 mkt | M5 mdl | M6 mkt | M6 mdl |
|-------|-----------|-----------|--------|--------|----------|----------|----------|----------|--------|--------|--------|--------|
| **R16** | 9/16 | 10/16 | 0.2257 | 0.2374 | 68.25% | 99.90% | 17.27% | 14.66% | 0.2207 | 0.2326 | 0.6239 | 0.6477 |
| **QF** | 6/8 | 6/8 | 0.3003 | 0.3109 | 29.92% | 33.09% | 14.43% | 15.97% | 0.1172 | 0.1182 | 0.3717 | 0.3847 |
| **SF** | 2/4 | 2/4 | 0.6325 | 0.6191 | 87.03% | 83.43% | 51.77% | 62.75% | 0.1060 | 0.1007 | 0.3640 | 0.3577 |
| **final** | 1/2 | 1/2 | 0.6476 | 0.6084 | 30.82% | 7.59% | 30.82% | 7.59% | 0.0503 | 0.0453 | 0.1586 | 0.1479 |
| **winner** | 0/1 | 0/1 | 0.8251 | 0.7261 | 76.15% | 35.08% | 76.15% | 35.08% | 0.0298 | 0.0253 | 0.1054 | 0.0878 |

_M1 = top-N marginal recall; M2 = qualifier Brier; M3 = cumulative to exact actual set (if never simulated, 99.90%); M4 = cumulative until all actual teams seen; M5 = all-team binary Brier; M6 = all-team binary log loss._

### R16

**Actual participants (16)** - 16 teams
> Argentina | Australia | Brazil | Croatia | England | France
> Japan | Morocco | Netherlands | Poland | Portugal | Senegal
> South Korea | Spain | Switzerland | United States

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **9/16** | **10/16** |
| Perfect set | no | no |
| Missed | Australia, Japan, Morocco, Poland, Senegal, South Korea, Switzerland | |
| | | Australia, Japan, Morocco, Senegal, South Korea, Switzerland |

**Market top-16 pick** - 16 teams
> Argentina | England | Brazil | France | Netherlands | Germany
> Spain | Portugal | Denmark | Belgium | Uruguay | Croatia
> Mexico | Ecuador | Serbia | United States

**Model top-16 pick** - 16 teams
> Argentina | Brazil | France | Netherlands | Spain | Portugal
> England | Denmark | Germany | Belgium | Uruguay | Croatia
> Ecuador | Poland | Serbia | United States

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.2257 | 0.2374 |
| Avg p on qualifiers | 60.81% | 59.39% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Australia, Brazil, Croatia, England, France, Japan, Morocco, Netherlands, Poland, Portugal, Senegal, South Korea, Spain, Switzerland, United States

| | Market | Model |
|--|--------|-------|
| Rank | 8,405 / 51,686 | not observed / 58,389 |
| p(actual set) | 0.00% | 0.00% |
| Cumulative through that rank | 68.25% | 99.90% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **243** |
| Cumulative probability | **17.27%** |
| Last actual team to appear | **Australia** |
| Combo at that rank | Argentina, Australia, Belgium, Brazil, Croatia, Ecuador, England, France, Germany, Mexico, Netherlands, Portugal, Serbia, Spain, United States, Uruguay |
| Union size (teams in ranks 1-243) | 31 |

**Actual teams covered** - 16 teams
> Argentina | Australia | Brazil | Croatia | England | France
> Japan | Morocco | Netherlands | Poland | Portugal | Senegal
> South Korea | Spain | Switzerland | United States

**Other teams in union (not in actual set)** - 15 teams
> Belgium | Cameroon | Canada | Denmark | Ecuador | Germany
> Ghana | Iran | Mexico | Qatar | Saudi Arabia | Serbia
> Tunisia | Uruguay | Wales

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **189** |
| Cumulative probability | **14.66%** |
| Last actual team to appear | **Australia** |
| Combo at that rank | Argentina, Australia, Belgium, Brazil, Croatia, Ecuador, England, France, Germany, Mexico, Netherlands, Portugal, Spain, Switzerland, United States, Uruguay |
| Union size (teams in ranks 1-189) | 31 |

**Actual teams covered** - 16 teams
> Argentina | Australia | Brazil | Croatia | England | France
> Japan | Morocco | Netherlands | Poland | Portugal | Senegal
> South Korea | Spain | Switzerland | United States

**Other teams in union (not in actual set)** - 15 teams
> Belgium | Cameroon | Canada | Denmark | Ecuador | Germany
> Ghana | Iran | Mexico | Qatar | Saudi Arabia | Serbia
> Tunisia | Uruguay | Wales

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.2207 | 0.2326 |
| Delta (model - market) | | +0.0119 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.6239 | 0.6477 |
| Delta (model - market) | | +0.0238 (market wins) |

### QF

**Actual participants (8)** - 8 teams
> Argentina | Brazil | Croatia | England | France | Morocco
> Netherlands | Portugal

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **6/8** | **6/8** |
| Perfect set | no | no |
| Missed | Croatia, Morocco | |
| | | Croatia, Morocco |

**Market top-8 pick** - 8 teams
> Brazil | England | France | Germany | Spain | Argentina
> Netherlands | Portugal

**Model top-8 pick** - 8 teams
> Brazil | Argentina | Netherlands | Spain | France | England
> Germany | Portugal

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.3003 | 0.3109 |
| Avg p on qualifiers | 49.19% | 47.51% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Brazil, Croatia, England, France, Morocco, Netherlands, Portugal

| | Market | Model |
|--|--------|-------|
| Rank | 399 / 38,891 | 894 / 45,637 |
| p(actual set) | 0.03% | 0.02% |
| Cumulative through that rank | 29.92% | 33.09% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **83** |
| Cumulative probability | **14.43%** |
| Last actual team to appear | **Morocco** |
| Combo at that rank | Argentina, Brazil, England, France, Germany, Morocco, Netherlands, Portugal |
| Union size (teams in ranks 1-83) | 23 |

**Actual teams covered** - 8 teams
> Argentina | Brazil | Croatia | England | France | Morocco
> Netherlands | Portugal

**Other teams in union (not in actual set)** - 15 teams
> Belgium | Denmark | Ecuador | Germany | Iran | Mexico
> Poland | Senegal | Serbia | Spain | Switzerland | Tunisia
> United States | Uruguay | Wales

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **202** |
| Cumulative probability | **15.97%** |
| Last actual team to appear | **Morocco** |
| Combo at that rank | Argentina, Brazil, England, France, Morocco, Netherlands, Portugal, Spain |
| Union size (teams in ranks 1-202) | 26 |

**Actual teams covered** - 8 teams
> Argentina | Brazil | Croatia | England | France | Morocco
> Netherlands | Portugal

**Other teams in union (not in actual set)** - 18 teams
> Belgium | Canada | Denmark | Ecuador | Germany | Iran
> Japan | Mexico | Poland | Qatar | Senegal | Serbia
> South Korea | Spain | Switzerland | United States | Uruguay | Wales

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1172 | 0.1182 |
| Delta (model - market) | | +0.0011 (market wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.3717 | 0.3847 |
| Delta (model - market) | | +0.0130 (market wins) |

### SF

**Actual participants (4)** - 4 teams
> Argentina | Croatia | France | Morocco

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **2/4** | **2/4** |
| Perfect set | no | no |
| Missed | Croatia, Morocco | |
| | | Croatia, Morocco |

**Market top-4 pick** - 4 teams
> Brazil | France | Argentina | England

**Model top-4 pick** - 4 teams
> Brazil | Argentina | France | Spain

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.6325 | 0.6191 |
| Avg p on qualifiers | 22.45% | 23.24% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, Croatia, France, Morocco

| | Market | Model |
|--|--------|-------|
| Rank | 990 / 5,732 | 1,023 / 6,528 |
| p(actual set) | 0.01% | 0.02% |
| Cumulative through that rank | 87.03% | 83.43% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **143** |
| Cumulative probability | **51.77%** |
| Last actual team to appear | **Morocco** |
| Combo at that rank | Argentina, Brazil, France, Morocco |
| Union size (teams in ranks 1-143) | 18 |

**Actual teams covered** - 4 teams
> Argentina | Croatia | France | Morocco

**Other teams in union (not in actual set)** - 14 teams
> Belgium | Brazil | Denmark | England | Germany | Mexico
> Netherlands | Portugal | Serbia | Spain | Switzerland | United States
> Uruguay | Wales

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **356** |
| Cumulative probability | **62.75%** |
| Last actual team to appear | **Morocco** |
| Combo at that rank | Argentina, Brazil, France, Morocco |
| Union size (teams in ranks 1-356) | 25 |

**Actual teams covered** - 4 teams
> Argentina | Croatia | France | Morocco

**Other teams in union (not in actual set)** - 21 teams
> Belgium | Brazil | Canada | Denmark | Ecuador | England
> Germany | Japan | Mexico | Netherlands | Poland | Portugal
> Qatar | Senegal | Serbia | South Korea | Spain | Switzerland
> United States | Uruguay | Wales

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.1060 | 0.1007 |
| Delta (model - market) | | -0.0054 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.3640 | 0.3577 |
| Delta (model - market) | | -0.0063 (model wins) |

### final

**Actual participants (2)** - 2 teams
> Argentina | France

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **1/2** | **1/2** |
| Perfect set | no | no |
| Missed | Argentina | |
| | | France |

**Market top-2 pick** - 2 teams
> Brazil | France

**Model top-2 pick** - 2 teams
> Brazil | Argentina

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.6476 | 0.6084 |
| Avg p on qualifiers | 19.53% | 22.04% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina, France

| | Market | Model |
|--|--------|-------|
| Rank | 7 / 405 | 2 / 441 |
| p(actual set) | 2.90% | 3.68% |
| Cumulative through that rank | 30.82% | 7.59% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **7** |
| Cumulative probability | **30.82%** |
| Last actual team to appear | **Argentina** |
| Combo at that rank | Argentina, France |
| Union size (teams in ranks 1-7) | 7 |

**Actual teams covered** - 2 teams
> Argentina | France

**Other teams in union (not in actual set)** - 5 teams
> Brazil | England | Germany | Portugal | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **2** |
| Cumulative probability | **7.59%** |
| Last actual team to appear | **Argentina** |
| Combo at that rank | Argentina, France |
| Union size (teams in ranks 1-2) | 3 |

**Actual teams covered** - 2 teams
> Argentina | France

**Other teams in union (not in actual set)** - 1 teams
> Brazil

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0503 | 0.0453 |
| Delta (model - market) | | -0.0049 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.1586 | 0.1479 |
| Delta (model - market) | | -0.0107 (model wins) |

### winner

**Actual participants (1)** - 1 teams
> Argentina

#### Metric 1 - Top-N by `p_at_least`

| | Market | Model |
|--|--------|-------|
| Recall | **0/1** | **0/1** |
| Perfect set | no | no |
| Missed | Argentina | |
| | | Argentina |

**Market top-1 pick** - 1 teams
> Brazil

**Model top-1 pick** - 1 teams
> Brazil

#### Metric 2 - Brier on actual qualifiers (`p_at_least`)

| | Market | Model |
|--|--------|-------|
| Mean Brier (qualifiers only) | 0.8251 | 0.7261 |
| Avg p on qualifiers | 9.16% | 14.79% |

#### Metric 3 - Exact actual set in joint distribution

Target combo: Argentina

| | Market | Model |
|--|--------|-------|
| Rank | 6 / 32 | 2 / 32 |
| p(actual set) | 9.16% | 14.79% |
| Cumulative through that rank | 76.15% | 35.08% |

#### Metric 4 - All actual teams seen in top combos

#### Market

| Field | Value |
|-------|-------|
| Stop at combo rank | **6** |
| Cumulative probability | **76.15%** |
| Last actual team to appear | **Argentina** |
| Combo at that rank | Argentina |
| Union size (teams in ranks 1-6) | 6 |

**Actual teams covered** - 1 teams
> Argentina

**Other teams in union (not in actual set)** - 5 teams
> Brazil | England | France | Germany | Spain

#### Model

| Field | Value |
|-------|-------|
| Stop at combo rank | **2** |
| Cumulative probability | **35.08%** |
| Last actual team to appear | **Argentina** |
| Combo at that rank | Argentina |
| Union size (teams in ranks 1-2) | 2 |

**Actual teams covered** - 1 teams
> Argentina

**Other teams in union (not in actual set)** - 1 teams
> Brazil

#### Metric 5 - All-team binary Brier

| | Market | Model |
|--|--------|-------|
| All-team Brier | 0.0298 | 0.0253 |
| Delta (model - market) | | -0.0045 (model wins) |

#### Metric 6 - All-team binary log loss

| | Market | Model |
|--|--------|-------|
| All-team log loss | 0.1054 | 0.0878 |
| Delta (model - market) | | -0.0176 (model wins) |

---

## Worked example - WC 2022 SF (model)

| | Metric 3 (exact set) | Metric 4 (all teams seen) |
|--|----------------------|---------------------------|
| Target | Argentina, Croatia, France, Morocco | Same four teams, any combo |
| Stop rank | 1,023 | **356** |
| Cumulative | 83.43% | **62.75%** |
| Trigger combo | exact quartet | Argentina, Brazil, France, Morocco (Morocco last) |

At rank 356 the model has seen every actual SF team at least once, but only 62.75% of simulated mass; the exact quartet needs rank 1,023 (83.43%).

Union at rank 356 (**25** teams): all four actual plus 21 others that appeared in high-frequency SF combos (see WC 2022 -> SF -> Metric 4 -> Model).
