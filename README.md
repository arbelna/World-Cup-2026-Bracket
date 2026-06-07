![FIFA World Cup 2026 Official Brand unveiled in Los Angeles](./Data_Collection/FIFA-World-Cup-26-Official-Brand-unveiled-in-Los-Angeles.png)

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

## Quick start

Requires Python 3.10+.

Each pipeline stage is self-contained and has its own `README.md` with setup instructions, prerequisites, and the exact commands to run:

- [`Data_Collection/README.md`](Data_Collection/README.md) — collect and normalize tournament inputs
- [`Match_model/README.md`](Match_model/README.md) — build the match dataset and run model evaluation
- [`Bracket_Simulations/README.md`](Bracket_Simulations/README.md) — simulate brackets and run backtests

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
