import numpy as np

def compute_similarity(a, b) -> float:
    """
    Cosine similarity between 2 embeddings.
    Returns value in [0..1] approximately.
    """
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)

    if a.shape != b.shape:
        raise ValueError("Embedding dimension mismatch")

    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0

    sim = float(np.dot(a, b) / denom)

    # normalize from [-1..1] to [0..1] (optional)
    return (sim + 1.0) / 2.0
