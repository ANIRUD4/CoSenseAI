"""
backend/storage/negative_store.py

Hard-Negative Prototype Store
==============================
Stores "hard negative" embeddings — samples the system misclassified — so
the inference engine can penalise its own past mistakes at decision time.

When the user corrects "No, this is Pen, not Pencil":
  - confirm.py calls  add_hard_negative("pencil", embedding, confused_with="pen")
  - The embedding is stored as a negative prototype for "pencil".

At inference time for label C:
  - infer.py checks how close the query is to C's hard negatives.
  - If the query is closer to a negative than to C's positives, C's similarity
    score is penalised, reducing false positives.

Storage format (data/hard_negatives.json)
-----------------------------------------
{
  "pencil": [
    {"vector": [...], "confused_with": "pen", "added_at": 1709000000.0},
    ...
  ]
}
"""

import json
import os
import time
from typing import Dict, List, Optional

NEGATIVE_STORE_PATH = "data/hard_negatives.json"

#: Max hard-negative prototypes stored per class (bounded memory).
MAX_NEGATIVES_PER_LABEL: int = 10


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_negatives() -> Dict[str, List[dict]]:
    """Load hard negatives dict from disk.  Returns {} if file not found."""
    if not os.path.exists(NEGATIVE_STORE_PATH):
        return {}
    with open(NEGATIVE_STORE_PATH, "r") as f:
        return json.load(f)


def _save_negatives(data: Dict[str, List[dict]]) -> None:
    os.makedirs(os.path.dirname(NEGATIVE_STORE_PATH), exist_ok=True)
    with open(NEGATIVE_STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ────────────────────────────────────────────────────────────────

def add_hard_negative(
    label: str,
    embedding: List[float],
    confused_with: Optional[str] = None,
) -> None:
    """
    Record `embedding` as a hard negative for `label`.

    Parameters
    ----------
    label        : The class that was INCORRECTLY predicted (the "false" class).
    embedding    : The embedding vector that was misclassified.
    confused_with: The correct class label (for debugging / display).
    """
    label = label.strip().lower()
    data = load_negatives()

    if label not in data:
        data[label] = []

    negatives = data[label]

    # Simple capacity cap: drop oldest if full
    if len(negatives) >= MAX_NEGATIVES_PER_LABEL:
        negatives.pop(0)  # evict oldest

    negatives.append({
        "vector": embedding,
        "confused_with": confused_with,
        "added_at": time.time(),
    })

    _save_negatives(data)
    print(
        f"HARD-NEG: Added negative for '{label}' "
        f"(confused_with='{confused_with}', total={len(negatives)})"
    )


def get_negative_vectors(label: str) -> List[List[float]]:
    """Return a list of hard-negative embedding vectors for `label`."""
    data = load_negatives()
    return [n["vector"] for n in data.get(label, [])]
