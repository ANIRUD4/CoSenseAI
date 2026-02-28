# learning/confidence.py

CONFIDENCE_THRESHOLD = 0.6


def is_confident(probability: float) -> bool:
    return probability >= CONFIDENCE_THRESHOLD
