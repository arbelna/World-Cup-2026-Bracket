![FIFA World Cup 2026 Official Brand unveiled in Los Angeles](./docs/img/FIFA-World-Cup-26-Official-Brand-unveiled-in-Los-Angeles.png)

# WorldCup2026 Bracket

`WorldCup2026 Bracket` is a three-stage pipeline for collecting international tournament data, training a match-level 1X2 probability model, and backtesting full tournament bracket simulations.

The project asks whether a small set of public pre-match signals can recover bookmaker-style match probabilities and still remain useful once those probabilities are pushed through full tournament brackets. In practice, the repo tests how far Elo, squad market values, confederation membership, and de-vigged bookmaker consensus can take the pipeline from historical data collection to bracket-level backtests.

## Pipeline

1. `Data_Collection`
   Collects and normalizes historical inputs such as Elo fixtures, bookmaker odds, squad lists, and squad market values.
2. `Match_model`
   Builds the historical match dataset and runs leave-one-tournament-out evaluation for the CatBoost match model and baseline methods.
3. `Bracket_Simulations`
   Simulates full World Cup brackets under market-derived and model-derived probabilities, then evaluates stage-level predictions against the historical outcomes.

```mermaid
---
config:
  layout: dagre
  theme: base
  themeVariables:
    background: '#F7F7F2'
    primaryTextColor: '#101010'
    lineColor: '#6B7280'
    fontFamily: 'Arial, sans-serif'
  themeCSS: |
    .cluster-label text,
    .cluster-label span {
      font-size: 18px !important;
      font-weight: 700 !important;
      fill: #101010 !important;
      color: #101010 !important;
    }
    .edgePath .path {
      stroke-width: 2px !important;
      stroke: #6B7280 !important;
    }
  flowchart:
    padding: 26
    rankSpacing: 28
    subGraphTitleMargin:
      top: 12
      bottom: 18
---
flowchart LR
    Elo["Elo ratings"]
    Odds["Bookmaker odds"]
    Squads["Squad lists"]
    Values["Squad market values"]

    subgraph DC["1. Data collection and normalization"]
        direction TD
        Collect["Collect historical tournament data"]
        Normalize["Normalize teams, formats, and sources"]
        Merge["Merge features and de-vig odds"]
        Collect --> Normalize --> Merge
    end

    Dataset[("Historical match dataset")]

    subgraph MM["2. Match-level probability model"]
        direction TD
        Features["Build pre-match features"]
        Train["Train CatBoost model"]
        Evaluate["Run leave-one-tournament-out evaluation<br/>and compare baselines"]
        Features --> Train --> Evaluate
    end

    Probabilities["Predicted 1X2 probabilities<br/>P(A win), P(draw), P(B win)"]

    subgraph BS["3. Bracket simulations and backtesting"]
        direction TD
        Rules["Apply tournament format<br/>and advancement rules"]
        Simulate["Simulate complete tournaments"]
        Backtest["Backtest stage-level predictions"]
        Results["Stage probabilities<br/>Likely matchups<br/>Market-vs-model reports"]

        Rules --> Simulate --> Backtest --> Results
    end


    Elo --> DC
    Odds --> DC
    Squads --> DC
    Values --> DC

    DC --> Dataset
    Dataset --> MM
    MM --> Probabilities
    Probabilities --> BS


    classDef input fill:#FFFFFF,stroke:#101010,stroke-width:2px,color:#101010;
    classDef dcNode fill:#B7F34A,stroke:#101010,stroke-width:2px,color:#101010;
    classDef mmNode fill:#56C7FF,stroke:#101010,stroke-width:2px,color:#101010;
    classDef bsNode fill:#FF6B57,stroke:#101010,stroke-width:2px,color:#101010;
    classDef bridge fill:#FFD84D,stroke:#101010,stroke-width:2px,color:#101010;
    classDef result fill:#101010,stroke:#101010,stroke-width:2px,color:#FFFFFF;

    class Elo,Odds,Squads,Values input;
    class Collect,Normalize,Merge dcNode;
    class Features,Train,Evaluate mmNode;
    class Rules,Simulate,Backtest bsNode;
    class Dataset,Probabilities bridge;
    class Results result;

    style DC fill:#EFFAD8,stroke:#101010,stroke-width:2px;
    style MM fill:#E3F6FF,stroke:#101010,stroke-width:2px;
    style BS fill:#FFE8E3,stroke:#101010,stroke-width:2px;
```

## Repository layout

- `Data_Collection/`: collectors, manifests, tests, and committed partition outputs.
- `Match_model/`: dataset build, model evaluation, committed experiment outputs, and report.
- `Bracket_Simulations/`: simulation engine, committed backtest summaries, and compare outputs.

## Results at a glance

The backtests indicate that a compact CatBoost model built from public pre-match signals can provide a useful foundation for full-tournament simulations.

At the match level, the model consistently outperforms the Elo baseline under leave-one-tournament-out evaluation. The improvement is visible across historical tournaments and remains strong on the WC2026 out-of-sample holdout. At the bracket level, the model is **competitive** with the market-derived baseline - matching it on recall while trailing on calibration and qualifier Brier. The goal is not to beat the market (which aggregates far more information) but to track it closely enough to be a reliable simulation foundation.

### Match-level probability estimates

The CatBoost model produces substantially lower held-out Brier scores than the Elo baseline in both match phases:

![Held-out Brier score by match phase](./docs/img/brier_by_phase.png)

A note on the baseline: Elo is primarily a team-strength rating. It is conceptually related to the FIFA world ranking, which also uses an Elo-style update procedure, although the two systems are not identical. Elo provides a strong and interpretable signal of relative team strength, but using it alone as a match-probability estimator is intentionally simple: it cannot fully capture factors such as squad composition, recent trends, tournament stage, or other match-specific conditions. The improvement below should therefore be interpreted as the value of combining a richer feature set with a more flexible probability model, rather than as evidence that Elo is a weak rating system. For the bracket backtests, the more demanding benchmark is the market-derived baseline.

The improvement is not driven by a single tournament. CatBoost achieves a lower Brier score than Elo in every historical leave-one-tournament-out fold shown below, with reductions ranging from **41% to 71%**. On the WC2026 holdout, the model records a **70% lower** Brier score than Elo.

![Brier score by tournament](./docs/img/brier_by_tournament.png)

Because the WC2026 holdout Brier score sits near the lower end of the historical range and the model's error is substantially lower for knockout-stage matches, I consider its probability estimates reliable enough to use as the foundation for the bracket simulations.

#### What the error looks like in practice

Brier score and cross-entropy are useful for comparing models but are hard to interpret directly. The headline figure is the weighted MAE: for each match, take the absolute difference between the model's probability and the de-vigged market consensus separately for home win, draw, and away win, then average across the three outcomes.

For the full leave-one-tournament-out evaluation the weighted MAE is **3.86 pp** per outcome on average. The table below applies that figure to a representative 1X2 line with a clear home favourite:

| Outcome | Market | Model | Δ pp |
|---------|--------|-------|------|
| Home win | 70.0% | 64.2% | −5.8 |
| Draw | 20.0% | 22.9% | +2.9 |
| Away win | 10.0% | 12.9% | +2.9 |
| **Macro MAE** | | | **3.87 pp** |

On the WC2026 out-of-sample holdout the figure is **3.68 pp**, placing the tournament comfortably within the historical range. The example below uses a representative group-stage line with a moderate favourite:

| Outcome | Market | Model | Δ pp |
|---------|--------|-------|------|
| Home win | 58.0% | 52.5% | −5.5 |
| Draw | 26.0% | 28.8% | +2.8 |
| Away win | 16.0% | 18.7% | +2.7 |
| **Macro MAE** | | | **3.67 pp** |

The error is not uniform across match types. Group-stage matches average **4.17 pp** while knockout matches average **2.99 pp** - consistent with the Brier chart above. Later-stage knockout matches involve stronger and more symmetrically rated teams where market and model signals converge.

#### Accuracy against actual match outcomes

The evaluation above scores predictions against the de-vigged market consensus, measuring how closely the model tracks market pricing. When scored instead against the 90-minute result, the market wins roughly **55% of per-game log-loss comparisons** across 558 held-out matches. The model trails on mean log-loss but leads on **top-1 correct picks** (54.1% vs 53.4%), getting 4 extra correct calls across 256 World Cup matches. When model and market pick different favourites (37 games), they split even on log-loss but the model wins 14 vs 10 on top-1.

| Metric | Market | Model |
|--------|--------|-------|
| Log-loss wins - all matches (558) | **305 - 54.7%** | 253 - 45.3% |
| Top-1 correct - all matches (558) | 298 - 53.4% | **302 - 54.1%** |
| Top-1 correct - World Cups only (256) | 133 - 52.0% | **137 - 53.5%** |
| Top-1 when favourites differ (37 games) | 10 | **14** |

This is the expected result rather than a failure: the model is trained to approximate market soft labels, so the market will always edge ahead when both are scored on the same hard-outcome measure. Log-loss also penalises confident wrong calls heavily - the model can simultaneously win more correct picks and lose mean log-loss if it assigns too much mass to those picks when they are wrong. Crucially, this does not undermine the bracket results. Bracket simulation chains many matches, and the probability shifts that cost the model on per-game log-loss can compound across a full tournament in ways that improve stage-level coverage. On the metrics that matter for bracket prediction - recall and cumulative coverage at the Final and Winner stages - the model leads the market. Full analysis in [`Match_model/results.md`](Match_model/results.md).


### Bracket-level backtesting

The full-bracket simulations are evaluated against the actual outcomes of the 2010–2022 World Cups. Three complementary metrics capture different dimensions of bracket quality.

**Top-N recall** - for each stage, does the simulation rank the teams that actually advanced among its highest-probability picks? A simulation that assigns high marginal probability to a team that genuinely reached, say, the semi-finals scores well here. Higher is better.

**Qualifier Brier** - for teams that actually reached a given stage, how confident was the simulation that they would? This measures calibration against actual outcomes: lower Brier means the simulation assigned higher probability to the teams that genuinely advanced.

**All-teams-seen cumulative coverage** - how far down the ranked list of bracket scenarios must you go before every team that actually advanced has appeared in at least one simulated combo? This is a scenario-coverage diagnostic: lower means all actual teams are reachable within a smaller probability budget. It does not directly measure whether the model assigns high probability to the right teams — a team satisfies the condition by appearing in any combo above the threshold, even a low-probability one.

**Recall: model edges market at every stage, but evidence is inconclusive at four tournaments**

The model has higher average Top-N recall at every stage of the bracket. The direction is consistent- +1.6 pp at R16, +3.1 at QF, +6.2 at SF, +12.5 at the Final.But with only four World Cups, a tournament-level block bootstrap (10,000 resamples) shows wide uncertainty, and the confidence interval for the model-minus-market recall gap includes zero at every stage.

![Bracket stage recall](./docs/img/bracket_stage_recall.png)

**Qualifier Brier: market leads at every stage**

The market-derived baseline has lower qualifier Brier at every stage, meaning it assigned slightly higher probability to the teams that actually advanced. The table below shows the arithmetic mean of the simulated reach-probabilities over the teams that actually qualified at each stage, computed directly from the committed simulation outputs:

| Stage | Market avg probability for actual qualifiers | Model avg probability | Gap |
|-------|----------------------------------------------|-----------------------|-----|
| R16 | 63.2% | 61.0% | 2.2 pp |
| QF | 46.9% | 42.5% | 4.4 pp |
| SF | 29.7% | 26.1% | 3.6 pp |
| Final | 19.7% | 17.9% | 1.8 pp |
| Winner | 12.4% | 11.4% | 1.0 pp |

The gap between the market and the model is 1–4 percentage points, depending on the stage, so the absolute improvement is modest. The more important pattern is the rising curve shared by both: even the eventual champion was assigned only around a 12% chance of winning the tournament by the market. This reflects the inherent uncertainty of knockout football, where a few upsets can reshape the entire bracket. That uncertainty is even more relevant for the 2026 World Cup, which expands to 48 teams and introduces an additional round of knockout matches.

Scoring all 32 teams as a binary reach/not-reach event (all-team Brier M5 and log loss M6) confirms the same pattern. On M5, the market leads at R16 (0.1920 vs 0.2007), QF (0.1261 vs 0.1338), and SF (0.0882 vs 0.0896); the model is marginally better at the Final (0.0502 vs 0.0494) and Winner (0.0275 vs 0.0270). On M6 the market leads at every stage, though the gap at the Final (0.1622 vs 0.1653) and Winner (0.0958 vs 0.0976) is negligible. The model also produces fewer top-N false positives at every stage. This rules out probability inflation as an explanation for the model's recall advantage: a model that simply gave every team a high probability would look good on recall but would accumulate false positives, which the model does not.


![Qualifier Brier by stage](./docs/img/qualifier_brier_by_stage.png)

**Cumulative coverage: model needs less probability mass to cover actual teams at late stages**

As a coverage diagnostic, a lower value means all actual teams appeared somewhere in the simulated joint distribution earlier (i.e. within a smaller slice of cumulative probability). The market needs less mass to cover actual teams at R16 and QF; the model needs less at the Final (−16.3 pp) and Winner (−13.5 pp). This does not mean the model assigns higher probability to the right teams at those stages — recall and Brier are the right metrics for that — but it does suggest its late-stage scenario space is less diffuse:

![All-teams-seen cumulative error by stage](./docs/img/cumulative_bracket_error.png)

Taken together: the market is better calibrated overall (ECE 0.0095 vs 0.0237) and leads on qualifier Brier at every stage. The model's calibration deficit is concentrated in the 0.5–0.7 probability range, where it consistently underrates mid-range favourites. On recall the model edges ahead at every stage; on late-stage cumulative coverage (a scenario-coverage diagnostic) it needs less probability mass to reach the actual finalists, though neither gap clears statistical significance at four tournaments. The honest summary is that the two approaches are close - the model is a viable simulation foundation, and closing the calibration gap on favourites is the clearest remaining improvement. Full analysis in [`Bracket_Simulations/results.md`](Bracket_Simulations/results.md).

**A note on simulation simplifications.** Because the simulator tracks only 1X2 outcomes and not exact scores, it cannot apply the real FIFA group-stage tiebreak sequence (goal difference → goals scored → head-to-head → lots). Instead it uses a pairwise-strength ranking among tied teams. For knockout draws, it replaces extra time and penalties with a single probabilistic advancement step weighted by each team's relative 90-minute win probability. These are known simplifications; the full treatment is in [`Bracket_Simulations/README.md`](Bracket_Simulations/README.md#simplifications-relative-to-real-fifa-rules).


## Quick start

Requires Python 3.10+.

Each pipeline stage is self-contained and has its own `README.md` with setup instructions, prerequisites, and the exact commands to run:

- [`Data_Collection/README.md`](Data_Collection/README.md) - collect and normalize tournament inputs
- [`Match_model/README.md`](Match_model/README.md) - build the match dataset and run model evaluation
- [`Bracket_Simulations/README.md`](Bracket_Simulations/README.md) - simulate brackets and run backtests

Run the stages in order.

## Sources and references

- World Football Elo Ratings: https://eloratings.net/
- OddsPortal football odds archive: https://www.oddsportal.com/football/
- Wikipedia tournament squad pages: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads
- Transfermarkt: https://www.transfermarkt.com/

These are the main external data sources behind the committed inputs. Stage-level READMEs describe how each source is used inside the pipeline.

## License

This repository is released under the MIT License. See [LICENSE](LICENSE).

Third-party data, trademarks, and external media are not covered by the MIT License and remain the property of their respective owners.
