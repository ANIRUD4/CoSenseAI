"""
backend/utils/diversity.py

Diversity-Based Prototype Selection
====================================
Replaces the fixed "store first K frames" policy with a greedy
maximum-distance algorithm.

Core idea
---------
An incoming embedding is only accepted into the prototype store if it is
*sufficiently different* from every embedding already stored for that label.
"Different enough" is measured by cosine distance  (1 - cosine_similarity).

A per-class cap (MAX_PROTOTYPES_PER_LABEL) bounds memory growth on the
edge device.  When the cap is reached, the oldest low-weight prototype is
evicted to make room for a new, diverse one.
"""

import numpy as np
from typing import List, Tuple

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

#: A new embedding must be at least this far (cosine distance) from every
#: existing prototype to be accepted.  0.25 ≈ cosine_sim ≤ 0.75 → diverse.
MIN_DIVERSITY: float = 0.25

#: Hard upper bound on prototypes per label.
MAX_PROTOTYPES_PER_LABEL: int = 15


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _cosine_distance(a: List[float], b: List[float]) -> float:
    """Returns cosine distance in [0, 2].  Higher = more different."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    if va.shape != vb.shape:
        return 2.0  # Maximally different if dimensions don't match
    
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0.0:
        return 1.0          # treat zero-vectors as fully distinct
    sim = float(np.dot(va, vb) / denom)
    return 1.0 - sim        # distance ∈ [0, 2]


def _min_distance_to_set(embedding: List[float], existing: List[List[float]]) -> float:
    """Minimum cosine distance between `embedding` and any vector in `existing`."""
    if not existing:
        return 2.0          # nothing to compare → maximally diverse
    return min(_cosine_distance(embedding, e) for e in existing)


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def is_diverse_enough(
    embedding: List[float],
    existing_vectors: List[List[float]],
    min_diversity: float = MIN_DIVERSITY,
) -> bool:
    """
    Gate check: returns True only if `embedding` is diverse enough to be
    stored alongside `existing_vectors`.

    Used by `add_prototype()` for single-embedding gating.
    """
    return _min_distance_to_set(embedding, existing_vectors) >= min_diversity


def select_diverse_prototypes(
    candidates: List[List[float]],
    existing_vectors: List[List[float]],
    min_diversity: float = MIN_DIVERSITY,
    max_count: int = MAX_PROTOTYPES_PER_LABEL,
) -> Tuple[List[List[float]], int]:
    """
    Greedy maximum-distance selection from a batch of `candidates`.

    Algorithm
    ---------
    1. Start with `existing_vectors` as the already-accepted set.
    2. Iterate over candidates; accept each if it clears `min_diversity`
       against the accumulated accepted set.
    3. Stop when `max_count` total prototypes (existing + newly accepted)
       would be reached.

    Returns
    -------
    (accepted, skipped_count)
        accepted      – list of embeddings from `candidates` that passed
        skipped_count – how many candidates were rejected as redundant
    """
    available_slots = max(0, max_count - len(existing_vectors))
    # Note: We don't block here if slots == 0 because add_prototype handles eviction.
    # We just use available_slots as a hint for how many to accept in this batch
    # if we want to avoid excessive evictions in a single commit.
    # For now, let's allow at least a few even if full.
    effective_slots = max(3, available_slots) 

    accepted: List[List[float]] = []
    # Running set = existing + what we have accepted so far in this batch
    running_set: List[List[float]] = list(existing_vectors)

    for cand in candidates:
        if len(accepted) >= effective_slots:
            break
        if _min_distance_to_set(cand, running_set) >= min_diversity:
            accepted.append(cand)
            running_set.append(cand)

    skipped = len(candidates) - len(accepted)
    return accepted, skipped


def find_eviction_candidate(prototypes: list) -> int:
    """
    Returns the index of the prototype to evict when the cap is full.

    Policy (composite LFU + weight + age score):
    1. Prefer prototypes with low weight AND low use count (least contributed).
    2. Among equal-scored candidates, prefer the oldest (smallest last_updated).
    Fallback: evict the single oldest prototype.

    This replaces the old "oldest with weight < 1.0" heuristic with a richer
    Least-Frequently-Used (LFU) inspired policy that avoids evicting the most
    informative prototypes even if they happen to be old.
    """
    import time as _time

    now = _time.time()

    def _score(p):
        weight = p.get("weight", 1.0)
        uses   = p.get("uses", 1)
        age    = now - p.get("last_updated", now)  # seconds since last update
        # Lower score → better candidate for eviction.
        # Penalise low-weight / low-use / long-unseen prototypes.
        return (weight * uses) / max(age + 1, 1)

    return min(range(len(prototypes)), key=lambda i: _score(prototypes[i]))
