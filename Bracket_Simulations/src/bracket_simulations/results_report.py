from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bracket_simulations.actual_results import EXPECTED_N, STAGES

MODES = ("market_all", "model_all")


def _pct(x: float) -> str:
    return f"{100.0 * x:.2f}%"


def write_results_md(results: list[dict[str, Any]], path: Path) -> None:
    lines: list[str] = []
    lines.append("# Bracket_Simulations - compare summary")
    lines.append("")
    lines.append(
        "> The concise historical backtest summary lives in [`results.md`](../../results.md). "
        "The detailed stage-by-stage backtest lives in `data/output/simulations/stage_prediction_backtest.md`."
    )
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append(
        "Compares **market_all** (de-vigged bookmaker `target_soft`) vs "
        "**model_all** (core-7 CatBoost pairwise) against actual tournament outcomes "
        "for WC 2010-2022; WC 2026 forward comparison is included separately."
    )
    lines.append("")

    historical = [r for r in results if "error" not in r and "market_all" in r]
    market_ref = [r for r in results if "error" not in r and r.get("comparison_mode") == "market_reference"]
    if not historical and not market_ref:
        lines.append("No simulation outputs found. Run `python main_cli.py run-all` first.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    if historical:
        lines.append("## Aggregate marginal metrics (Brier on `p_at_least_*`)")
        lines.append("")
        lines.append(
            "Lower Brier is better; for a single binary reach event, a 50/50 guess scores 0.25 and a perfect prediction scores 0.00."
        )
        lines.append("")
        lines.append("| Stage | Market wins | Model wins | Ties |")
        lines.append("|-------|-------------|------------|------|")
        for stage in STAGES:
            m_w = d_w = t_w = 0
            for r in historical:
                ms = r["market_all"]["marginal"][stage]["brier"]
                ds = r["model_all"]["marginal"][stage]["brier"]
                if ms < ds:
                    m_w += 1
                elif ds < ms:
                    d_w += 1
                else:
                    t_w += 1
            lines.append(f"| {stage} | {m_w} | {d_w} | {t_w} |")

        lines.append("")
        lines.append("## Aggregate top-K hits")
        lines.append("")
        lines.append("| Stage | Market wins | Model wins | Ties |")
        lines.append("|-------|-------------|------------|------|")
        for stage in STAGES:
            m_w = d_w = t_w = 0
            for r in historical:
                ms = r["market_all"]["marginal"][stage]["topn_hits"]
                ds = r["model_all"]["marginal"][stage]["topn_hits"]
                if ms > ds:
                    m_w += 1
                elif ds > ms:
                    d_w += 1
                else:
                    t_w += 1
            lines.append(f"| {stage} | {m_w} | {d_w} | {t_w} |")

        champ_m = sum(1 for r in historical if r["market_all"]["champion_pick"] == r["champion_actual"])
        champ_d = sum(1 for r in historical if r["model_all"]["champion_pick"] == r["champion_actual"])
        lines.append("")
        lines.append(f"**Champion top-1 correct:** market {champ_m}/{len(historical)}, model {champ_d}/{len(historical)}")
        avg_p_m = sum(r["market_all"]["p_winner_actual"] for r in historical) / len(historical)
        avg_p_d = sum(r["model_all"]["p_winner_actual"] for r in historical) / len(historical)
        lines.append(f"**Avg p(winner) on actual champion:** market {_pct(avg_p_m)}, model {_pct(avg_p_d)}")
        lines.append("")

    if historical:
        lines.append("## Joint stage-configuration metrics")
        lines.append("")
        lines.append(
            "For each stage, probability assigned to the exact set of teams that reached "
            "that stage in the actual tournament."
        )
        lines.append("")
        lines.append("| Stage | Market avg p(actual) | Model avg p(actual) | Market top-1 hit | Model top-1 hit |")
        lines.append("|-------|----------------------|---------------------|------------------|-----------------|")
        for stage in STAGES:
            p_m = sum(r["market_all"]["joint"][stage]["p_joint_actual"] for r in historical) / len(historical)
            p_d = sum(r["model_all"]["joint"][stage]["p_joint_actual"] for r in historical) / len(historical)
            t1_m = sum(1 for r in historical if r["market_all"]["joint"][stage]["top1_correct"])
            t1_d = sum(1 for r in historical if r["model_all"]["joint"][stage]["top1_correct"])
            lines.append(f"| {stage} | {_pct(p_m)} | {_pct(p_d)} | {t1_m}/{len(historical)} | {t1_d}/{len(historical)} |")
        lines.append("")

    if market_ref:
        lines.append("## Market-reference comparisons (no actual outcomes yet)")
        lines.append("")
        lines.append(
            "For tournaments without played results, compare `model_all` probabilities against "
            "`market_all` reference probabilities on available stages."
        )
        lines.append("")
        lines.append("| Tournament | Stage | MAE(model vs market) | MSE(model vs market) |")
        lines.append("|------------|-------|----------------------|----------------------|")
        for r in market_ref:
            for stage in r.get("stages_compared", []):
                m = r.get("market_reference", {}).get(stage, {})
                lines.append(
                    f"| {r.get('competition', r.get('tournament'))} | {stage} | "
                    f"{float(m.get('mae_model_vs_market', 0.0)):.4f} | "
                    f"{float(m.get('mse_model_vs_market', 0.0)):.4f} |"
                )
        lines.append("")

    for r in historical:
        lines.append(f"## {r['competition']} ({r['tournament']})")
        lines.append("")
        lines.append(f"Actual champion: **{r['champion_actual']}**")
        lines.append(
            f"- Market pick: {r['market_all']['champion_pick']} "
            f"({_pct(r['market_all']['p_winner_actual'])} on actual)"
        )
        lines.append(
            f"- Model pick: {r['model_all']['champion_pick']} "
            f"({_pct(r['model_all']['p_winner_actual'])} on actual)"
        )
        lines.append("")

        lines.append("### Marginal reach")
        lines.append("")
        lines.append("| Stage | Metric | Market | Model | Better |")
        lines.append("|-------|--------|--------|-------|--------|")
        for stage in STAGES:
            n = EXPECTED_N[stage]
            for key, label in [("topn_hits", f"top-{n}"), ("brier", "Brier")]:
                mv = r["market_all"]["marginal"][stage][key]
                dv = r["model_all"]["marginal"][stage][key]
                if key == "brier":
                    better = "market" if mv < dv else ("model" if dv < mv else "tie")
                else:
                    better = "market" if mv > dv else ("model" if dv > mv else "tie")
                lines.append(f"| {stage} | {label} | {mv:.4f} | {dv:.4f} | {better} |")

        lines.append("")
        lines.append("### Joint configurations")
        lines.append("")
        actual_qf = ", ".join(r["actual_config"]["QF"])
        lines.append(f"Teams that reached QF ({len(r['actual_config']['QF'])}): {actual_qf}")
        lines.append("")
        lines.append("| Stage | p(actual) market | p(actual) model | Rank mkt | Rank mdl | Top-1 mkt | Top-1 mdl |")
        lines.append("|-------|------------------|-----------------|----------|----------|-----------|-----------|")
        for stage in STAGES:
            jm = r["market_all"]["joint"][stage]
            jd = r["model_all"]["joint"][stage]
            lines.append(
                f"| {stage} | {_pct(jm['p_joint_actual'])} | {_pct(jd['p_joint_actual'])} | "
                f"{jm['rank_actual']} | {jd['rank_actual']} | "
                f"{'yes' if jm['top1_correct'] else 'no'} | {'yes' if jd['top1_correct'] else 'no'} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
