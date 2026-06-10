"""
Refined WC26-inspired plots for Match Model & Bracket Simulations results.

The theme is intentionally WC26-inspired rather than a copy of FIFA artwork:
- three-host accent ribbon (Canada / Mexico / USA)
- red, green and blue tournament accents
- clean editorial layout suitable for README files and reports
- consistent model/baseline semantics and compact annotations

Generates 7 PNG files in docs/img/ (matching README.md image references):
  1. wc26_ce_holdout_vs_historical_refined.png  (no README reference, informational)
  2. brier_by_phase.png
  3. brier_by_tournament.png
  4. bracket_stage_recall.png
  5. cumulative_bracket_error.png
  6. qualifier_brier_by_stage.png
  7. top10_knockout_paths.png

Run from the WorldCup2026 Bracket repo root:
    python plot_wc26_refined.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
import numpy as np

# ---------------------------------------------------------------------------
# WC26-inspired palette
# ---------------------------------------------------------------------------
PAPER       = "#F7F3EA"   # warm editorial paper
INK         = "#0F172A"   # navy-black text
MUTED       = "#64748B"   # secondary text
GRID        = "#D8DEE9"   # subtle grid
CARD        = "#FFFDF8"   # card background
CARD_EDGE   = "#E5E7EB"

CANADA_RED  = "#D62839"
MEXICO_GREEN= "#008F5A"
USA_BLUE    = "#1D4ED8"
GOLD        = "#F4B942"

MODEL       = MEXICO_GREEN
BASELINE    = USA_BLUE
MARKET      = "#7C879B"
BAD         = CANADA_RED
GOOD        = MEXICO_GREEN

CATBOOST_LABEL = "CatBoost"
ELO_LABEL      = "Elo"

OUT_DIR = Path(__file__).parent / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_JSON = Path(__file__).parent / "data" / "model.json"

# ---------------------------------------------------------------------------
# Shared style helpers
# ---------------------------------------------------------------------------
# Shared figure title block (used by every chart)
FIG_TITLE_Y = 0.925
FIG_SUBTITLE_Y = 0.887
FIG_SUBTITLE_Y_WIDE = 0.872   # extra space between title and subtitle
FIG_PLOT_TOP = 0.78
FIG_PLOT_TOP_BRIER = 0.84     # brier-by-tournament: title-to-plot gap

# Typography (shared across all charts)
FS_HEADER = 8
FS_FOOTER = 10.5
FS_TITLE = 21
FS_SUBTITLE = 12.5
FS_AXIS_LABEL = 10.5
FS_TICK = 10
FS_ANNOT = 9
FS_LEGEND = 10

# Bracket subplot header offsets (figure coords above each axes top)
STAGE_LABEL_OFFSET = 0.028
AVG_BOX_OFFSET = 0.006
BRACKET_HSPACE = 0.38
def _add_wc26_header(fig: plt.Figure, kicker: str = "WORLD CUP 2026 MODEL RESEARCH") -> None:
    """Add a small 3-host visual ribbon and editorial kicker."""
    y = 0.975
    x0 = 0.035
    total_w = 0.28
    h = 0.010
    seg = total_w / 3
    for i, color in enumerate((CANADA_RED, MEXICO_GREEN, USA_BLUE)):
        fig.add_artist(
            mpatches.FancyBboxPatch(
                (x0 + i * seg, y), seg - 0.004, h,
                transform=fig.transFigure,
                boxstyle="round,pad=0,rounding_size=0.004",
                facecolor=color, edgecolor="none", zorder=20,
            )
        )
    fig.text(x0 + total_w + 0.012, y + 0.001, kicker,
             ha="left", va="bottom", fontsize=FS_HEADER, fontweight="bold", color=MUTED)
    fig.text(0.965, y + 0.001, "CANADA  •  MEXICO  •  USA",
             ha="right", va="bottom", fontsize=FS_HEADER, color=MUTED)


def _add_wc26_footer(fig: plt.Figure) -> None:
    fig.text(0.035, 0.018, "WC26 backtest visuals • arbelna",
             ha="left", va="bottom", fontsize=FS_FOOTER, color=MUTED)
    # fig.text(0.035, 0.018, "ar",
    #          ha="right", va="bottom", fontsize=16, fontweight="bold", color=INK)


def _apply_wc26_style(fig: plt.Figure, ax: plt.Axes, *, grid_axis: str = "y") -> None:
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(CARD)
    ax.tick_params(colors=INK, labelsize=FS_TICK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)
    for spine in ax.spines.values():
        spine.set_edgecolor(CARD_EDGE)
        spine.set_linewidth(0.9)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, linestyle="-", alpha=0.7)
    ax.set_axisbelow(True)


def _title(
    fig: plt.Figure,
    title: str,
    subtitle: str,
    *,
    subtitle_y: float | None = None,
) -> None:
    fig.text(0.035, FIG_TITLE_Y, title, ha="left", va="top",
             fontsize=FS_TITLE, fontweight="bold", color=INK)
    fig.text(0.035, subtitle_y if subtitle_y is not None else FIG_SUBTITLE_Y,
             subtitle, ha="left", va="top", fontsize=FS_SUBTITLE, color=MUTED)


def _scatter_split_dot(
    ax: plt.Axes,
    x: float,
    y: float,
    *,
    size: float = 86,
    left_color: str,
    right_color: str,
    edgecolor: str = "white",
    linewidth: float = 0.8,
    zorder: int = 4,
) -> None:
    """Draw a circular marker with vertical half-and-half fill."""
    diameter = np.sqrt(size)
    r = diameter / 2.0
    da = DrawingArea(diameter, diameter)
    for theta1, theta2, fc in ((90, 270, left_color), (270, 450, right_color)):
        da.add_artist(
            mpatches.Wedge(
                (r, r), r, theta1, theta2,
                facecolor=fc,
                edgecolor=edgecolor,
                linewidth=linewidth,
            )
        )
    ax.add_artist(
        AnnotationBbox(
            da, (x, y),
            xycoords=ax.transData,
            frameon=False,
            pad=0,
            box_alignment=(0.5, 0.5),
            zorder=zorder,
        )
    )


def _legend(ax: plt.Axes, handles: list, **kwargs) -> None:
    ax.legend(handles=handles, frameon=False, labelcolor=INK, fontsize=FS_LEGEND, **kwargs)


def _save(fig: plt.Figure, name: str) -> Path:
    out = OUT_DIR / name
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)
    print(f"  saved -> {out.name}")
    return out


def _fmt_pp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f} pp"


def _load_model_json() -> dict:
    with MODEL_JSON.open("r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # File may be truncated after the teams array; close the outer object and retry
        teams_end = raw.find('"top_configs"')
        if teams_end == -1:
            teams_end = len(raw)
        # Walk back to the last ] before any incomplete key
        last_bracket = raw.rfind("]", 0, teams_end)
        if last_bracket != -1:
            return json.loads(raw[: last_bracket + 1] + "\n}")
        raise


def _knockout_path_segments(probs: dict[str, float]) -> list[float]:
    """Convert cumulative reach probabilities into exclusive finish buckets."""
    segments = [
        1.0 - probs["R32"],
        probs["R32"] - probs["R16"],
        probs["R16"] - probs["QF"],
        probs["QF"] - probs["SF"],
        probs["SF"] - probs["final"],
        probs["final"] - probs["winner"],
        probs["winner"],
    ]
    return [max(0.0, value) for value in segments]


# ===========================================================================
# Chart 1 – WC2026 holdout CE vs historical LOTO CE
# ===========================================================================
def plot_ce_holdout_vs_historical() -> None:
    # Values from Match_model/results.md Section 2 (CatBoost CE per fold)
    historical_ce = [
        0.9273, 0.9183, 0.9191, 0.9237,  # Copa Am 2016, 2019, 2021, 2024
        1.0315, 1.0019, 0.9600, 0.9709,  # Euro 2012, 2016, 2020, 2024
        0.9761, 0.9784, 0.9626, 0.9510,  # WC 2010, 2014, 2018, 2022
    ]
    wc26_ce = 0.9214  # Match_model/results.md Section 6
    avg = float(np.mean(historical_ce))
    lo, hi = min(historical_ce), max(historical_ce)

    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(fig, "WC2026 holdout cross-entropy", "CatBoost holdout performance compared with historical leave-one-tournament-out folds")
    _apply_wc26_style(fig, ax, grid_axis="y")
    plt.subplots_adjust(left=0.11, right=0.96, bottom=0.16, top=FIG_PLOT_TOP)

    rng = np.random.default_rng(7)
    jitter = rng.uniform(-0.12, 0.12, len(historical_ce))

    ax.axhspan(lo, hi, color=USA_BLUE, alpha=0.055, zorder=0)
    ax.axhline(avg, color=MUTED, linewidth=1.3, linestyle="--", zorder=1)
    ax.scatter(jitter, historical_ce, s=72, color=BASELINE, alpha=0.78,
               edgecolor="white", linewidth=0.8, zorder=3)
    ax.scatter([1], [wc26_ce], s=320, marker="*", color=GOLD,
               edgecolor=INK, linewidth=0.8, zorder=5)

    ax.text(0.18, avg + 0.0012, f"Historical mean  {avg:.4f}", color=MUTED, fontsize=FS_ANNOT, va="bottom")
    ax.text(0.00, hi + 0.002, f"range  {lo:.4f}–{hi:.4f}", color=MUTED, fontsize=FS_ANNOT, ha="center")
    ax.text(1, wc26_ce - 0.005, f"WC2026 holdout\n{wc26_ce:.4f}", ha="center", va="top",
            fontsize=FS_TICK, fontweight="bold", color=INK)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Historical LOTO folds", "WC2026 holdout"], fontsize=FS_TICK)
    ax.set_xlim(-0.45, 1.45)
    ax.set_ylabel("Cross-entropy  ·  lower is better", fontsize=FS_AXIS_LABEL)
    ax.set_ylim(lo - 0.006, hi + 0.009)

    _legend(ax, [
        plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=BASELINE, label="Historical folds"),
        plt.Line2D([], [], marker="*", linestyle="", markersize=13, color=GOLD, markeredgecolor=INK, label="WC2026 holdout"),
    ], loc="upper right")

    _save(fig, "wc26_ce_holdout_vs_historical_refined.png")


# ===========================================================================
# Chart 2 – Group vs Knockout held-out Brier score
# ===========================================================================
def plot_group_vs_knockout_brier() -> None:
    # Values from Match_model/results.md Section 3 (Group vs Knockout Brier)
    buckets = ["Group stage\n(n=410)", "Knockout stage\n(n=148)"]
    cb_vals = np.array([0.0107, 0.0069])
    elo_vals = np.array([0.0227, 0.0143])
    gains = (elo_vals - cb_vals) / elo_vals

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(
        fig, "Held-out Brier score by match phase",
        "CatBoost consistently improves on the Elo baseline, with the largest relative gain in knockout matches",
        subtitle_y=FIG_SUBTITLE_Y_WIDE,
    )
    _apply_wc26_style(fig, ax, grid_axis="x")
    plt.subplots_adjust(left=0.18, right=0.96, bottom=0.16, top=FIG_PLOT_TOP)

    y = np.arange(len(buckets))[::-1]
    for yi, elo, cb, gain in zip(y, elo_vals, cb_vals, gains):
        ax.plot([cb, elo], [yi, yi], color=GRID, linewidth=7, solid_capstyle="round", zorder=1)
        ax.scatter([elo], [yi], s=150, color=BASELINE, edgecolor="white", linewidth=1, zorder=3)
        ax.scatter([cb], [yi], s=150, color=MODEL, edgecolor="white", linewidth=1, zorder=4)
        ax.text(cb - 0.00035, yi - 0.20, f"{cb:.4f}", color=MODEL, fontsize=FS_ANNOT, ha="right", fontweight="bold")
        ax.text(elo + 0.00035, yi - 0.20, f"{elo:.4f}", color=BASELINE, fontsize=FS_ANNOT, ha="left", fontweight="bold")
        ax.text((cb + elo) / 2, yi + 0.19, f"{gain:.0%} lower", color=GOOD, fontsize=FS_ANNOT,
                ha="center", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(buckets, fontsize=FS_TICK)
    ax.set_xlabel("Brier score  ·  lower is better", fontsize=FS_AXIS_LABEL)
    ax.set_xlim(0, 0.0245)
    ax.set_ylim(-0.55, 1.55)

    _legend(ax, [
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=MODEL, label=CATBOOST_LABEL),
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=BASELINE, label=ELO_LABEL),
    ], loc="lower right", ncol=2)

    _save(fig, "brier_by_phase.png")


# ===========================================================================
# Chart 3 – Brier score per tournament: CatBoost vs Elo + WC2026 holdout
# ===========================================================================
def plot_brier_per_tournament() -> None:
    # Values from Match_model/results.md Section 2 + Section 6 (Brier per tournament)
    comps = [
        "Copa Am. 2016", "Copa Am. 2019", "Copa Am. 2021", "Copa Am. 2024",
        "Euro 2012", "Euro 2016", "Euro 2020", "Euro 2024",
        "WC 2010", "WC 2014", "WC 2018", "WC 2022", "WC2026 holdout",
    ]
    cb = np.array([
        0.0120, 0.0201, 0.0102, 0.0093,
        0.0122, 0.0097, 0.0071, 0.0085,
        0.0087, 0.0103, 0.0071, 0.0091, 0.0065,
    ])
    elo = np.array([
        0.0227, 0.0368, 0.0202, 0.0216,
        0.0258, 0.0144, 0.0210, 0.0168,
        0.0193, 0.0170, 0.0205, 0.0219, 0.0228,
    ])
    gains = (elo - cb) / elo

    fig, ax = plt.subplots(figsize=(10.8, 8.3))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(fig, "Brier score by tournament", "Leave-one-tournament-out evaluation; the final row is the WC2026 out-of-sample holdout")
    _apply_wc26_style(fig, ax, grid_axis="x")
    plt.subplots_adjust(left=0.20, right=0.96, bottom=0.11, top=FIG_PLOT_TOP_BRIER)

    y = np.arange(len(comps))[::-1]
    for idx, (yi, label, elo_v, cb_v, gain) in enumerate(zip(y, comps, elo, cb, gains)):
        is_holdout = label == "WC2026 holdout"
        line_color = GOLD if is_holdout else GRID
        line_width = 8 if is_holdout else 5
        ax.plot([cb_v, elo_v], [yi, yi], color=line_color, linewidth=line_width,
                alpha=0.70 if is_holdout else 1, solid_capstyle="round", zorder=1)
        ax.scatter([elo_v], [yi], s=105 if not is_holdout else 170, color=BASELINE,
                   marker="*" if is_holdout else "o", edgecolor="white", linewidth=0.9, zorder=3)
        ax.scatter([cb_v], [yi], s=105 if not is_holdout else 170, color=MODEL,
                   marker="*" if is_holdout else "o", edgecolor="white", linewidth=0.9, zorder=4)
        ax.text(max(elo_v, cb_v) + 0.0010, yi, f"{gain:.0%} lower", va="center",
                fontsize=FS_ANNOT, color=GOOD, fontweight="bold")

    ax.axhline(0.5, color=GOLD, linewidth=1.2, linestyle="--", alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(comps, fontsize=FS_TICK)
    for tick in ax.get_yticklabels():
        if tick.get_text() == "WC2026 holdout":
            tick.set_color(INK)
            tick.set_fontweight("bold")
    ax.set_xlabel("Brier score  ·  lower is better", fontsize=FS_AXIS_LABEL)
    ax.set_xlim(0, 0.043)
    ax.set_ylim(-0.8, len(comps) - 0.2)

    _legend(ax, [
        plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=MODEL, label=CATBOOST_LABEL),
        plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=BASELINE, label=ELO_LABEL),
        plt.Line2D([], [], marker="*", linestyle="", markersize=11, color=GOLD, markeredgecolor=INK, label="WC2026 holdout row"),
    ], loc="lower right")

    _save(fig, "brier_by_tournament.png")


# ===========================================================================
# Chart 4 – Bracket Stage Recall: Model vs Market (WC 2010–2022)
# ===========================================================================
def plot_bracket_stage_recall() -> None:
    tournaments = ["WC 2010", "WC 2014", "WC 2018", "WC 2022"]
    # Values from Bracket_Simulations/results.md per-tournament tables
    # Tournaments: WC 2010, 2014, 2018, 2022
    data = {
        "R16":   {"market": [75.00, 62.50, 87.50, 56.25], "model": [68.75, 68.75, 81.25, 62.50]},
        "QF":    {"market": [62.50, 62.50, 50.00, 75.00], "model": [62.50, 62.50, 62.50, 75.00]},
        "SF":    {"market": [25.00, 75.00, 25.00, 50.00], "model": [25.00, 50.00, 75.00, 50.00]},
        "Final": {"market": [50.00, 0.00, 0.00, 50.00],   "model": [50.00, 50.00, 0.00, 50.00]},
    }

    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.6), sharex=True)
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(fig, "Bracket stage recall", "Top-N recall by World Cup and stage; green indicates the simulation model, grey indicates the market baseline")
    plt.subplots_adjust(
        left=0.09, right=0.97, bottom=0.11, top=FIG_PLOT_TOP,
        wspace=0.17, hspace=BRACKET_HSPACE,
    )

    stage_accents = {"R16": GOLD, "QF": USA_BLUE, "SF": CANADA_RED, "Final": MEXICO_GREEN}
    for ax, stage in zip(axes.flat, data):
        _apply_wc26_style(fig, ax, grid_axis="x")
        y = np.arange(len(tournaments))[::-1]
        market = np.array(data[stage]["market"])
        model = np.array(data[stage]["model"])
        delta = model - market
        agg_mk = float(np.mean(market))
        agg_md = float(np.mean(model))

        ax.set_yticks(y)
        ax.set_yticklabels(tournaments, fontsize=FS_TICK)
        ax.set_xlim(0, 104)
        ax.set_xlabel("Recall (%)", fontsize=FS_AXIS_LABEL)

        for yi, mk, md, d in zip(y, market, model, delta):
            ax.plot([mk, md], [yi, yi], color=GRID, linewidth=5, solid_capstyle="round", zorder=1)
            if np.isclose(mk, md):
                _scatter_split_dot(
                    ax, mk, yi, size=86,
                    left_color=MARKET, right_color=MODEL,
                )
            else:
                ax.scatter([mk], [yi], s=86, color=MARKET, edgecolor="white", linewidth=0.8, zorder=3)
                ax.scatter([md], [yi], s=86, color=MODEL, edgecolor="white", linewidth=0.8, zorder=4)
            ax.text(max(mk, md) + 2.2, yi, _fmt_pp(d), va="center", fontsize=FS_ANNOT,
                    color=GOOD if d >= 0 else BAD, fontweight="bold")

        pos = ax.get_position()
        fig.text(
            pos.x0, pos.y1 + STAGE_LABEL_OFFSET, stage,
            transform=fig.transFigure, ha="left", va="bottom",
            fontsize=FS_SUBTITLE, fontweight="bold", color=stage_accents[stage],
        )
        fig.text(
            pos.x0, pos.y1 + AVG_BOX_OFFSET, f"Average:  {agg_mk:.0f}% → {agg_md:.0f}%",
            transform=fig.transFigure, ha="left", va="bottom", fontsize=FS_ANNOT, color=MUTED,
            bbox=dict(boxstyle="round,pad=0.22", facecolor=PAPER, edgecolor=CARD_EDGE),
        )

    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=MODEL, label="Model"),
        plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=MARKET, label="Market"),
    ]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.965, 0.875), frameon=False,
               ncol=2, fontsize=FS_LEGEND, labelcolor=INK)

    _save(fig, "bracket_stage_recall.png")


# ===========================================================================
# Chart 5 – M4 all-teams-seen cumulative
# ===========================================================================
def plot_m4_cumulative() -> None:
    # Values from Bracket_Simulations/results.md M4 all-teams-seen cumulative table
    stages = ["R16", "QF", "SF", "Final", "Winner"]
    market = np.array([9.29, 14.38, 24.11, 35.91, 56.86])
    model = np.array([7.85, 15.04, 27.55, 19.87, 45.23])
    delta = model - market

    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(
        fig, "All-teams-seen cumulative error",
        "Average across WC 2010–2022; lower values indicate a better simulation fit",
        subtitle_y=FIG_SUBTITLE_Y_WIDE,
    )
    _apply_wc26_style(fig, ax, grid_axis="y")
    plt.subplots_adjust(left=0.10, right=0.96, bottom=0.16, top=FIG_PLOT_TOP)

    x = np.arange(len(stages))
    for xi, mk, md, d in zip(x, market, model, delta):
        ax.plot([xi, xi], [mk, md], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
        ax.scatter([xi], [mk], s=125, color=MARKET, edgecolor="white", linewidth=0.9, zorder=3)
        ax.scatter([xi], [md], s=125, color=MODEL, edgecolor="white", linewidth=0.9, zorder=4)
        ytop = max(mk, md) + 4.0
        winner = "Model" if md < mk else "Market"
        ax.text(xi, ytop, f"{abs(d):.2f} pp\n{winner} better", ha="center", va="bottom",
                fontsize=FS_ANNOT, color=GOOD if md < mk else BAD, fontweight="bold")
        ax.text(xi - 0.07, mk, f"{mk:.2f}%", ha="right", va="center", fontsize=FS_ANNOT, color=MARKET)
        ax.text(xi + 0.07, md, f"{md:.2f}%", ha="left", va="center", fontsize=FS_ANNOT, color=MODEL, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=FS_TICK)
    ax.set_ylabel("Cumulative probability (%)  ·  lower is better", fontsize=FS_AXIS_LABEL)
    ax.set_ylim(0, 72)
    ax.set_xlim(-0.45, len(stages) - 0.55)

    _legend(ax, [
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=MODEL, label="Model"),
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=MARKET, label="Market"),
    ], loc="upper left", ncol=2)

    _save(fig, "cumulative_bracket_error.png")


# ===========================================================================
# Chart 6 – M2 qualifier Brier: Market vs Model per stage
# ===========================================================================
def plot_m2_qualifier_brier() -> None:
    """
    Qualifier Brier: mean squared error on the teams that actually reached
    each stage, using their simulated marginal p_at_least_{stage}.
    Market wins at every stage — this chart presents that honestly.
    Data from Bracket_Simulations/results.md (WC 2010-2022 average).
    """
    # Values from Bracket_Simulations/results.md M2 qualifier Brier table
    stages = ["R16", "QF", "SF", "Final", "Winner"]
    market = np.array([0.1955, 0.3246, 0.5138, 0.6489, 0.7687])
    model  = np.array([0.2086, 0.3585, 0.5580, 0.6725, 0.7811])
    delta  = model - market  # all positive: market is better

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(
        fig, "Qualifier Brier by stage",
        "Mean squared error on teams that actually reached each stage · lower is better · market leads at every stage",
        subtitle_y=FIG_SUBTITLE_Y_WIDE,
    )
    _apply_wc26_style(fig, ax, grid_axis="y")
    plt.subplots_adjust(left=0.10, right=0.96, bottom=0.16, top=FIG_PLOT_TOP)

    x = np.arange(len(stages))
    for xi, mk, md, d in zip(x, market, model, delta):
        # connector
        ax.plot([xi, xi], [mk, md], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
        # dots
        ax.scatter([xi], [mk], s=125, color=MARKET, edgecolor="white", linewidth=0.9, zorder=3)
        ax.scatter([xi], [md], s=125, color=MODEL,  edgecolor="white", linewidth=0.9, zorder=4)
        # delta annotation above the model dot
        ytop = md + 0.038
        ax.text(xi, ytop, f"+{d:.4f}\nMarket better", ha="center", va="bottom",
                fontsize=FS_ANNOT, color=MUTED, fontweight="bold")
        # value labels to the sides
        ax.text(xi - 0.08, mk, f"{mk:.4f}", ha="right", va="center",
                fontsize=FS_ANNOT, color=MARKET)
        ax.text(xi + 0.08, md, f"{md:.4f}", ha="left", va="center",
                fontsize=FS_ANNOT, color=MODEL, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=FS_TICK)
    ax.set_ylabel("Qualifier Brier  ·  lower is better", fontsize=FS_AXIS_LABEL)
    ax.set_ylim(0, 0.97)
    ax.set_xlim(-0.50, len(stages) - 0.50)

    _legend(ax, [
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=MODEL,  label="Model"),
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=MARKET, label="Market"),
    ], loc="upper left", ncol=2)

    _save(fig, "qualifier_brier_by_stage.png")


# ===========================================================================
# Chart 7 - Top 10 WC2026 teams knockout path distribution
# ===========================================================================
def plot_top10_knockout_paths() -> None:
    payload = _load_model_json()
    teams = payload["teams"]
    generated = payload.get("meta", {}).get("generated", "")[:10]
    ranked = sorted(
        teams,
        key=lambda team: (
            float(team["probs"]["winner"]),
            float(team["probs"]["final"]),
            float(team["probs"]["SF"]),
        ),
        reverse=True,
    )[:10]

    # 1 stacked bar per team, group-exit excluded.
    # Segments are exclusive finish buckets, stacked bottom→top:
    #   Winner (gold) at base, R32 exit at top — bar height = P(reach R32).
    segment_labels = ["Winner", "Final loss", "SF exit", "QF exit", "R16 exit", "R32 exit"]
    segment_colors = [GOLD, CANADA_RED, MEXICO_GREEN, "#14B8A6", USA_BLUE, "#BFDBFE"]

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    _add_wc26_header(fig)
    _add_wc26_footer(fig)
    _title(
        fig,
        "Top 10 teams - knockout path probabilities",
        (
            "WC2026 model probabilities ranked by title chance; "
            f"stacked bars show exclusive knockout finish buckets"
        ),
        subtitle_y=FIG_SUBTITLE_Y_WIDE,
    )
    _apply_wc26_style(fig, ax, grid_axis="y")
    plt.subplots_adjust(left=0.08, right=0.97, bottom=0.30, top=FIG_PLOT_TOP)

    ordered = ranked  # best team on the left
    x = np.arange(len(ordered))

    # Compute exclusive segments in bottom→top order (reverse of _knockout_path_segments)
    def _segments_reversed(probs: dict) -> list[float]:
        segs = _knockout_path_segments(probs)  # [group_exit, R32_exit, R16_exit, QF_exit, SF_exit, final_loss, winner]
        return [max(0.0, s) for s in [segs[6], segs[5], segs[4], segs[3], segs[2], segs[1]]]

    bottom = np.zeros(len(ordered))
    for idx, (label, color) in enumerate(zip(segment_labels, segment_colors)):
        values = np.array([_segments_reversed(t["probs"])[idx] * 100.0 for t in ordered])
        ax.bar(
            x, values,
            bottom=bottom,
            width=0.68,
            color=color,
            edgecolor=CARD,
            linewidth=0.8,
            label=label,
            zorder=3,
        )
        bottom += values

    # Win% annotation above each bar (= above R32 probability)
    for xi, team in zip(x, ordered):
        winner_pct = float(team["probs"]["winner"]) * 100.0
        bar_top    = float(team["probs"]["R32"])    * 100.0
        ax.text(
            xi, bar_top + 0.8,
            f"{winner_pct:.1f}%",
            ha="center", va="bottom",
            fontsize=FS_ANNOT, color=INK, fontweight="bold",
        )

    max_bar = max(float(t["probs"]["R32"]) * 100.0 for t in ordered)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [team["name"] for team in ordered],
        fontsize=FS_TICK, rotation=22, ha="right",
    )
    ax.set_ylim(0, max_bar + 9)
    yticks = np.arange(0, int(max_bar) + 21, 20)
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{t:.0f}%" for t in yticks], fontsize=FS_TICK)
    ax.set_ylabel("Tournament outcome share", fontsize=FS_AXIS_LABEL)
    ax.set_xlim(-0.5, len(ordered) - 0.5)

    ax.legend(
        handles=[mpatches.Patch(color=c, label=l) for l, c in zip(segment_labels, segment_colors)],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=len(segment_labels),
        frameon=False,
        labelcolor=INK,
        fontsize=FS_LEGEND,
    )

    _save(fig, "top10_knockout_paths.png")


if __name__ == "__main__":
    print("Generating refined WC26-inspired plots …")
    plot_ce_holdout_vs_historical()
    plot_group_vs_knockout_brier()
    plot_brier_per_tournament()
    plot_bracket_stage_recall()
    plot_m4_cumulative()
    plot_m2_qualifier_brier()
    plot_top10_knockout_paths()
    print(f"\nAll 7 refined plots saved to:\n  {OUT_DIR}")
