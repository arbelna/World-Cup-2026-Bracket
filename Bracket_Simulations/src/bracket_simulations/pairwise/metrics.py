from __future__ import annotations

PROB_EPS = 1e-15


def normalize_probs(probs):
    import numpy as np

    clipped = np.clip(probs, PROB_EPS, None)
    return clipped / clipped.sum(axis=1, keepdims=True)
