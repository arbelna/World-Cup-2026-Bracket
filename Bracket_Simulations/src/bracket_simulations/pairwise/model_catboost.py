from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

from bracket_simulations.pairwise.metrics import normalize_probs
from bracket_simulations.pairwise.rows import MatchRow


class CatBoostCore7Model:
    def __init__(
        self,
        *,
        iterations: int = 100,
        depth: int = 4,
        learning_rate: float = 0.1,
        random_state: int = 42,
    ) -> None:
        self.iterations = iterations
        self.depth = depth
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.model_ = None
        self.scaler_ = StandardScaler()

    def fit(self, x: np.ndarray, y: np.ndarray) -> CatBoostCore7Model:
        from catboost import CatBoostClassifier, Pool

        self.scaler_.fit(x)
        x_scaled = self.scaler_.transform(x)
        self.model_ = CatBoostClassifier(
            loss_function="MultiCrossEntropy",
            iterations=self.iterations,
            depth=self.depth,
            learning_rate=self.learning_rate,
            random_seed=self.random_state,
            verbose=False,
            allow_writing_files=False,
        )
        self.model_.fit(Pool(data=x_scaled, label=y))
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("Model is not fitted")
        x_scaled = self.scaler_.transform(x)
        raw = self.model_.predict(x_scaled, prediction_type="Probability")
        return normalize_probs(np.asarray(raw, dtype=float))


def fit_predict(train_rows: list[MatchRow], test_rows: list[MatchRow], *, random_state: int = 42) -> np.ndarray:
    from bracket_simulations.pairwise.rows import rows_to_feature_matrix, rows_to_label_matrix

    x_train = rows_to_feature_matrix(train_rows)
    y_train = rows_to_label_matrix(train_rows)
    x_test = rows_to_feature_matrix(test_rows)
    model = CatBoostCore7Model(random_state=random_state)
    model.fit(x_train, y_train)
    return model.predict_proba(x_test)
