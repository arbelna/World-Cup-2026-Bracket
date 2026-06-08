from __future__ import annotations

import numpy as np


def block_bootstrap_delta(
    per_tournament_model: list[float],
    per_tournament_market: list[float],
    *,
    n_boot: int = 10_000,
    seed: int = 42,
) -> dict[str, float | int]:
    """Bootstrap the mean (model - market) gap by resampling whole tournaments.

    Each list holds one value per tournament for a single (stage, metric),
    e.g. per-tournament recall = hits / EXPECTED_N[stage].
    """
    model = np.asarray(per_tournament_model, dtype=float)
    market = np.asarray(per_tournament_market, dtype=float)
    delta = model - market                      # paired per tournament
    n = len(delta)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))  # resample tournaments w/ replacement
    boot_means = delta[idx].mean(axis=1)
    return {
        "delta_mean": float(delta.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
        "n_tournaments": n,
        "n_model_better": int((delta > 0).sum()),
        "n_market_better": int((delta < 0).sum()),
        "significant": bool(np.percentile(boot_means, 2.5) > 0
                            or np.percentile(boot_means, 97.5) < 0),
    }
