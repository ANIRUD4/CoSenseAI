import math
from typing import List


def softmax(scores: List[float], temperature: float = 0.05) -> List[float]:
    """
    Convert similarity scores into calibrated confidence.
    Lower temperature = sharper decisions.
    """

    if not scores:
        return []

    max_score = max(scores)  # numerical stability

    exp_scores = [
        math.exp((s - max_score) / temperature)
        for s in scores
    ]

    total = sum(exp_scores)

    return [e / total for e in exp_scores]
