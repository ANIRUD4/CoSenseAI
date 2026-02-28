# learning/incremental_learner.py

import numpy as np
from sklearn.linear_model import SGDClassifier

from learning.model_registry import load_model, save_model


class IncrementalLearner:
    def __init__(self, embedding_dim: int):
        self.embedding_dim = embedding_dim
        self.model = load_model()
        self.seen_labels = set()
        self.buffer_X = []
        self.buffer_y = []

        if self.model is None:
            self.model = SGDClassifier(
                loss="log_loss",
                max_iter=1,
                learning_rate="optimal",
                warm_start=True
            )
            self.is_initialized = False
        else:
            self.is_initialized = True
            self.seen_labels = set(self.model.classes_)

    def learn(self, embedding: list, label: str):
        X = np.array(embedding).reshape(1, -1)
        y = label

        self.seen_labels.add(label)

        # Buffer until we have at least 2 classes
        self.buffer_X.append(X)
        self.buffer_y.append(y)

        if not self.is_initialized:
            if len(self.seen_labels) < 2:
                # Not enough classes to initialize model
                return

            # Initialize model with buffered data
            X_init = np.vstack(self.buffer_X)
            y_init = np.array(self.buffer_y)

            self.model.partial_fit(X_init, y_init, classes=list(self.seen_labels))
            self.is_initialized = True
            self.buffer_X.clear()
            self.buffer_y.clear()
        else:
            self.model.partial_fit(X, np.array([y]))

        save_model(self.model)

    def predict(self, embedding: list):
        if not self.is_initialized:
            return {
                "label": "unknown",
                "confidence": 0.0
            }

        X = np.array(embedding).reshape(1, -1)
        probs = self.model.predict_proba(X)[0]
        labels = self.model.classes_

        idx = probs.argmax()

        return {
            "label": labels[idx],
            "confidence": float(probs[idx])
        }
