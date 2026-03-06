"""
learning/interface.py

Optional SGD Refinement Layer
=============================
The core recognition logic in `infer.py` uses prototype similarity directly.
This module is an optional incremental SGD layer that can be enabled via
`IncrementalLearner.ENABLE_SGD_REFINEMENT`.

Embedding dimension is imported from `perception.interface` so it tracks
whatever engine tier is active (512 for CLIP ViT-B/32).
"""

from learning.incremental_learner import IncrementalLearner

# Import canonical embedding dim from perception layer.
# Falls back to 512 (CLIP default) if perception module unavailable at import time.
try:
    from perception.interface import EMBEDDING_DIM
except Exception:
    EMBEDDING_DIM = 512

# Singleton learner instance
_LEARNER = IncrementalLearner(embedding_dim=EMBEDDING_DIM)


def predict(embedding: list) -> dict:
    """
    Returns the predicted label and confidence from the optional SGD model.
    Returns 'unknown' if SGD refinement is disabled.
    """
    return _LEARNER.predict(embedding)


def update(embedding: list, label: str | None):
    """
    Incrementally updates the optional SGD model with a new pair.
    No-op if SGD refinement is disabled.
    """
    if label is None:
        return
    _LEARNER.learn(embedding, label)