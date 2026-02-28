from learning.incremental_learner import IncrementalLearner

# Singleton learner instance
# embedding_dim MUST match perception output
_LEARNER = IncrementalLearner(embedding_dim=1024)


def predict(embedding: list[float]) -> dict:
    """
    Returns the predicted label and confidence for a given embedding.
    Does NOT update or retrain the model.
    """
    return _LEARNER.predict(embedding)


def update(embedding: list[float], label: str | None):
    """
    Incrementally updates the model with a new (embedding, label) pair.
    If label is None, no learning occurs.
    """
    if label is None:
        return

    _LEARNER.learn(embedding, label)