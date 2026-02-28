import random

LABELS = ["Paracetamol", "Vitamin D", "Blood Pressure Medicine"]

def predict(embedding: list[float]) -> dict:
    """
    Mock prediction.
    """
    return {
        "label": random.choice(LABELS),
        "confidence": round(random.uniform(0.6, 0.9), 2)
    }

def update(embedding: list[float], label: str):
    """
    Mock update.
    Does nothing intentionally.
    """
    return
