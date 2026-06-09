from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

from match_model.metrics import normalize_probs
from match_model.rows import CORE7_FEATURE_NAMES, MatchRow


class FoldScaler:
    def __init__(self, scaler: StandardScaler | None) -> None:
        self.scaler = scaler

    @classmethod
    def fit(cls, x_train: np.ndarray) -> FoldScaler:
        scaler = StandardScaler()
        scaler.fit(x_train)
        return cls(scaler)

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.scaler is None:
            return x
        return self.scaler.transform(x)


class CatBoostCore7Model:
    """CatBoost multiclass model on 7 core match features with soft-label targets."""

    def __init__(
        self,
        *,
        iterations: int = 100,
        depth: int = 4,
        learning_rate: float = 0.1,
        random_state: int = 42,
        train_dir: Path | None = None,
    ) -> None:
        self.iterations = iterations
        self.depth = depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.train_dir = train_dir
        self.model_ = None
        self.feature_names: tuple[str, ...] = CORE7_FEATURE_NAMES

    def fit(self, x: np.ndarray, y: np.ndarray) -> CatBoostCore7Model:
        from catboost import CatBoostClassifier, Pool

        params: dict[str, object] = {
            "loss_function": "MultiCrossEntropy",
            "iterations": self.iterations,
            "depth": self.depth,
            "learning_rate": self.learning_rate,
            "random_seed": self.random_state,
            "verbose": False,
            "allow_writing_files": False,
        }
        if self.train_dir is not None:
            params["train_dir"] = str(self.train_dir)
            params["allow_writing_files"] = True

        self.model_ = CatBoostClassifier(**params)
        pool = Pool(data=x, label=y)
        self.model_.fit(pool)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("Model is not fitted")
        raw = self.model_.predict(x, prediction_type="Probability")
        return normalize_probs(np.asarray(raw, dtype=float))


def rows_to_feature_matrix(
    rows: list[MatchRow],
    feature_names: tuple[str, ...] = CORE7_FEATURE_NAMES,
) -> np.ndarray:
    return np.vstack([row.feature_vector(feature_names) for row in rows])


def rows_to_label_matrix(rows: list[MatchRow]) -> np.ndarray:
    return np.vstack([row.y_soft for row in rows])
