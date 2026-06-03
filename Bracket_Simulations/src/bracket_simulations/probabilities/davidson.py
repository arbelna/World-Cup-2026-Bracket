from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def davidson_90min_probs(pi_a: float, pi_b: float, nu: float) -> tuple[float, float, float]:
    sqrt_ab = math.sqrt(pi_a * pi_b)
    denom = pi_a + pi_b + nu * sqrt_ab
    if denom <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    w_a = pi_a / denom
    w_b = pi_b / denom
    p_draw = (nu * sqrt_ab) / denom
    return w_a, p_draw, w_b


def et_win_prob_team_a(w_a: float, w_b: float) -> float:
    denom = w_a + w_b
    if denom <= 0:
        return 0.5
    return 0.5 + 0.5 * (w_a - w_b) / (2.0 * denom)


@dataclass(frozen=True)
class DavidsonModel:
    strengths: dict[str, float]
    nu: float

    def win_probs(self, team_a: str, team_b: str) -> tuple[float, float]:
        pi_a = self.strengths[team_a]
        pi_b = self.strengths[team_b]
        w_a, _, w_b = davidson_90min_probs(pi_a, pi_b, self.nu)
        return w_a, w_b

    def probs_90min(self, team_a: str, team_b: str) -> tuple[float, float, float]:
        pi_a = self.strengths[team_a]
        pi_b = self.strengths[team_b]
        return davidson_90min_probs(pi_a, pi_b, self.nu)

    def et_win_prob_team_a(self, team_a: str, team_b: str) -> float:
        w_a, w_b = self.win_probs(team_a, team_b)
        return et_win_prob_team_a(w_a, w_b)

    @classmethod
    def fit_from_matches(cls, matches: list[dict], teams: list[str]) -> DavidsonModel:
        team_index = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        obs_a: list[int] = []
        obs_b: list[int] = []
        targets: list[tuple[float, float, float]] = []

        for m in matches:
            target = m.get("target_soft")
            if target is None:
                continue
            a = str(m["team_a"])
            b = str(m["team_b"])
            if a not in team_index or b not in team_index:
                continue
            ta, td, tb = float(target[0]), float(target[1]), float(target[2])
            s = ta + td + tb
            if s <= 0:
                continue
            obs_a.append(team_index[a])
            obs_b.append(team_index[b])
            targets.append((ta / s, td / s, tb / s))

        if not targets:
            raise ValueError("No market matches with target_soft to fit Davidson model.")

        y = np.asarray(targets, dtype=float)
        ia = np.asarray(obs_a, dtype=int)
        ib = np.asarray(obs_b, dtype=int)

        def neg_log_likelihood(params: np.ndarray) -> float:
            log_pi = params[:n]
            log_nu = params[n]
            pi = np.exp(log_pi)
            nu = math.exp(log_nu)
            pi_a = pi[ia]
            pi_b = pi[ib]
            sqrt_ab = np.sqrt(pi_a * pi_b)
            denom = pi_a + pi_b + nu * sqrt_ab
            w_a = pi_a / denom
            w_b = pi_b / denom
            p_d = (nu * sqrt_ab) / denom
            probs = np.stack([w_a, p_d, w_b], axis=1)
            probs = np.clip(probs, 1e-15, 1.0)
            return float(-np.sum(y * np.log(probs)))

        x0 = np.zeros(n + 1, dtype=float)
        x0[n] = math.log(0.25)
        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B")
        if not result.success:
            logger.warning("Davidson fit did not converge: %s", result.message)

        log_pi = result.x[:n]
        pi = {teams[i]: float(math.exp(log_pi[i])) for i in range(n)}
        nu = float(math.exp(result.x[n]))
        logger.info("Fitted Davidson on %d matches (%d teams, nu=%.4f).", len(targets), n, nu)
        return cls(strengths=pi, nu=nu)
