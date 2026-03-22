"""
backend/utils/diversity.py

Centroid-Based Prototype Selection
=====================================
Replaces the old greedy max-distance algorithm with unsupervised K-Means
clustering to extract clean, noise-free prototype centroids from captured frames.

Core idea
---------
When the user teaches the system a new object (multi-shot learning), k frames
are captured. Instead of saving all k raw embeddings (which are noisy), we:

  1. Run K-Means on the k candidate embeddings.
  2. Extract the geometric centroids of each cluster.
  3. Store ONLY the centroids — perfectly averaged, noise-cancelled vectors.

Benefits
--------
- Noise cancellation: camera vibration, glare, and blur average out.
- Inference speedup: 2–3 centroid comparisons vs up to 100 raw frames.
- Stable confidence: similarity scores no longer spike due to saved noise.

The per-class memory cap (MAX_PROTOTYPES_PER_LABEL) and LFU eviction policy
are preserved to protect edge-device RAM.
"""

import numpy as np
from typing import List, Tuple

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

#: Number of centroids to extract per learning session.
#: 2–3 is optimal: covers major viewpoint variations without bloat.
N_CENTROIDS: int = 3

#: Hard upper bound on prototypes (centroids) per label.
#: Much less pressure is now expected on this cap since we store centroids, not raw frames.
MAX_PROTOTYPES_PER_LABEL: int = 100

#: Legacy gate used by `is_diverse_enough()` (single-embedding gating, still used for
#: single-shot feedback flows). Not used in the multishot clustering path.
MIN_DIVERSITY: float = 0.15


# ──────────────────────────────────────────────────────────────
# Internal helpers (kept for single-shot feedback flow)
# ──────────────────────────────────────────────────────────────

def _cosine_distance(a: List[float], b: List[float]) -> float:
    """Returns cosine distance in [0, 2].  Higher = more different."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    if va.shape != vb.shape:
        return 2.0
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0.0:
        return 1.0
    sim = float(np.dot(va, vb) / denom)
    return 1.0 - sim


def _min_distance_to_set(embedding: List[float], existing: List[List[float]]) -> float:
    """Minimum cosine distance between `embedding` and any vector in `existing`."""
    if not existing:
        return 2.0
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

    Used by `add_prototype()` for single-embedding gating (feedback/confirm flows).
    """
    return _min_distance_to_set(embedding, existing_vectors) >= min_diversity


def extract_centroids(
    candidates: List[List[float]],
    n_centroids: int = N_CENTROIDS,
) -> List[List[float]]:
    """
    Distil a batch of raw candidate embeddings into `n_centroids` clean vectors
    using K-Means clustering.

    Algorithm
    ---------
    1. Stack candidates into an (N, D) matrix.
    2. Run K-Means with k = min(n_centroids, N) clusters.
    3. Return the cluster centres as pristine, averaged prototype vectors.

    Each returned centroid is L2-normalised so it is directly comparable
    to CLIP-space query embeddings using cosine similarity.

    Parameters
    ----------
    candidates  : list of raw embedding vectors from the capture burst.
    n_centroids : number of cluster centres to extract (default: 3).

    Returns
    -------
    list of L2-normalised centroid vectors (shape: [n_centroids, D]).
    """
    from sklearn.cluster import KMeans

    if not candidates:
        return []

    X = np.array(candidates, dtype=np.float32)
    n = len(candidates)

    # Can't have more clusters than data points.
    k = min(n_centroids, n)

    if k == 1:
        # Single frame or single cluster — just return the mean.
        centroid = X.mean(axis=0)
        centroids = [centroid]
    else:
        # n_init="auto" silences sklearn's future warning; random_state for reproducibility.
        km = KMeans(n_clusters=k, n_init="auto", random_state=42, max_iter=300)
        km.fit(X)
        centroids = [km.cluster_centers_[i] for i in range(k)]

    # L2-normalise each centroid so cosine similarity works correctly.
    result = []
    for c in centroids:
        norm = np.linalg.norm(c)
        if norm > 0:
            c = c / norm
        result.append(c.tolist())

    return result


def select_diverse_prototypes(
    candidates: List[List[float]],
    existing_vectors: List[List[float]],
    min_diversity: float = MIN_DIVERSITY,
    max_count: int = MAX_PROTOTYPES_PER_LABEL,
) -> Tuple[List[List[float]], int]:
    """
    Centroid-based replacement for the old greedy distance loop.

    Workflow
    --------
    1. Extract N_CENTROIDS clean centroids from the incoming candidates via K-Means.
    2. Filter out any centroids that are too similar to already-stored prototypes
       (using the same MIN_DIVERSITY gate as before to prevent redundancy across sessions).
    3. Return (accepted_centroids, n_skipped).

    This preserves the original function signature so that call sites in
    `orchestrator.py` require only a comment update (no API breakage).
    """
    if not candidates:
        return [], 0

    # Step 1: Extract clean centroids from the noisy raw captures.
    centroids = extract_centroids(candidates, n_centroids=N_CENTROIDS)

    # Step 2: Gate centroids against existing prototypes (cross-session dedup).
    accepted: List[List[float]] = []
    running_set: List[List[float]] = list(existing_vectors)

    for centroid in centroids:
        if len(existing_vectors) + len(accepted) >= max_count:
            break
        if _min_distance_to_set(centroid, running_set) >= min_diversity:
            accepted.append(centroid)
            running_set.append(centroid)

    skipped_raw = len(candidates) - len(accepted)
    return accepted, skipped_raw


def find_eviction_candidate(prototypes: list) -> int:
    """
    Returns the index of the prototype to evict when the cap is full.

    Policy (composite LFU + weight + age score):
    1. Prefer prototypes with low weight AND low use count (least contributed).
    2. Among equal-scored candidates, prefer the oldest (smallest last_updated).
    Fallback: evict the single oldest prototype.
    """
    import time as _time

    now = _time.time()

    def _score(p):
        weight = p.get("weight", 1.0)
        uses   = p.get("uses", 1)
        age    = now - p.get("last_updated", now)
        return (weight * uses) / max(age + 1, 1)

    return min(range(len(prototypes)), key=lambda i: _score(prototypes[i]))
