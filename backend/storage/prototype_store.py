"""
backend/storage/prototype_store.py

Prototype store with diversity gating and per-class mean-vector caching.

Mean-vector caching
-------------------
After every add or update operation the class mean vector is recomputed and
stored under the "mean_vector" key in the prototype JSON.  This allows the
inference route to run a single O(1) dot-product per class instead of
an O(P) loop over all individual prototypes when a class has ≥ MIN_FOR_MEAN
prototypes — giving better accuracy (true centroid) at lower cost.
"""

import json
import os
import time
from typing import Dict, List, Optional

import numpy as np

from backend.utils.diversity import (
    is_diverse_enough,
    find_eviction_candidate,
    MAX_PROTOTYPES_PER_LABEL,
    MIN_DIVERSITY,
)

STORE_PATH = "data/prototypes.json"

# Minimum number of prototypes needed before the mean vector is trusted as
# the primary inference target (fewer → use best-individual-prototype instead).
MIN_FOR_MEAN: int = 3


# ── Low-level helpers ──────────────────────────────────────────────────────

def _compute_cosine_sim(a, b) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _compute_mean_vector(prototypes: list) -> Optional[List[float]]:
    """
    Return the L2-normalised mean of all prototype vectors.
    Returns None if the list is empty.
    """
    vectors = [p["vector"] for p in prototypes if "vector" in p]
    if not vectors:
        return None
    mean = np.mean([np.array(v, dtype=np.float32) for v in vectors], axis=0)
    norm = np.linalg.norm(mean)
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def _incremental_update_mean(old_mean: Optional[List[float]], count: int, new_vec: List[float]) -> List[float]:
    """
    Cumulative Moving Average update: 
    new_mean = (old_mean * count + new_vec) / (count + 1)
    """
    new_v = np.array(new_vec, dtype=np.float32)
    if old_mean is None or count == 0:
        # First example
        norm = np.linalg.norm(new_v)
        if norm > 0:
            new_v = new_v / norm
        return new_v.tolist()
    if old_mean is not None and count > 0:
        if len(old_mean) != len(new_vec):
            # Dimension mismatch: reject update to avoid poisoning the mean
            return old_mean

    m = np.array(old_mean, dtype=np.float32) if old_mean is not None else None
    # Cumulative mean
    if m is not None:
        updated = (m * count + new_v) / (count + 1)
    else:
        updated = new_v
    
    # Always normalize to keep on the unit sphere for cosine similarity
    norm = np.linalg.norm(updated)
    if norm > 0:
        updated = updated / norm
    return updated.tolist()


# ── I/O ────────────────────────────────────────────────────────────────────

def load_prototypes() -> Dict:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, "r") as f:
        return json.load(f)


def save_prototypes(data: Dict):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Mean-vector helpers (public) ────────────────────────────────────────────

def get_mean_vector(label: str) -> Optional[List[float]]:
    """
    Return the cached L2-normalised mean vector for `label`, or None if the
    label is unknown or has no prototypes.
    """
    data = load_prototypes()
    return data.get(label, {}).get("mean_vector", None)


def _refresh_mean(data: Dict, label: str):
    """Recompute and cache mean_vector for `label` in-place within `data`."""
    protos = data.get(label, {}).get("prototypes", [])
    mean = _compute_mean_vector(protos)
    if label in data:
        data[label]["mean_vector"] = mean


# ── Core operations ────────────────────────────────────────────────────────

def add_prototype(
    label: str,
    embedding: List[float],
    action: str = None,
    source: str = "user",
) -> bool:
    """
    Diversity-Gated Add with mean-vector refresh.

    Stores the embedding only when it is sufficiently different from every
    existing prototype (cosine distance ≥ MIN_DIVERSITY).  When the per-class
    cap is full the weakest/oldest prototype is evicted first.

    After a successful add the class mean_vector is recomputed and cached.

    Returns True if the embedding was stored, False if rejected as redundant.
    """
    data = load_prototypes()

    if label not in data:
        data[label] = {"prototypes": [], "mean_vector": None, "total_count": 0}
    
    # Ensure total_count exists for legacy data
    if "total_count" not in data[label]:
        data[label]["total_count"] = len(data[label].get("prototypes", []))

    protos = data[label]["prototypes"]
    old_mean = data[label].get("mean_vector")
    count = data[label].get("total_count", 0)

    # ── Dimension Safety Check ─────────────────────────────────────────────
    # Prevent mixed-engine contamination (e.g., CLIP 512-d vs MobileNet 1024-d)
    if old_mean is not None:
        if len(embedding) != len(old_mean):
            print(
                f"WARNING: Dimension mismatch for '{label}'. "
                f"Existing: {len(old_mean)}, New: {len(embedding)}. "
                f"Dropping new embedding to prevent store corruption."
            )
            return False

    # ── Incremental Mean Update (Instant Learning) ─────────────────────────
    # We update the mean even if the point is rejected from the diverse buffer
    # because the mean represents the "global drift" of the class.
    data[label]["mean_vector"] = _incremental_update_mean(old_mean, count, embedding)
    data[label]["total_count"] = count + 1

    # ── Diversity gate (for individual handles) ────────────────────────────
    existing_vectors = [p["vector"] for p in protos]
    if not is_diverse_enough(embedding, existing_vectors, min_diversity=MIN_DIVERSITY):
        print(
            f"DIVERSITY: Skipped '{label}' buffer addition (redundant) — "
            f"Updated incremental mean only."
        )
        save_prototypes(data)
        return True # Return true because the class mean DID learn from it

    # ── Cap enforcement ────────────────────────────────────────────────────
    if len(protos) >= MAX_PROTOTYPES_PER_LABEL:
        evict_idx = find_eviction_candidate(protos)
        evicted   = protos.pop(evict_idx)
        print(f"DIVERSITY: Buffer full for '{label}' — evicted oldest/weakest.")

    # ── Store new prototype ────────────────────────────────────────────────
    protos.append({
        "vector":       embedding,
        "weight":       1.0,
        "uses":         1,
        "action":       action,
        "source":       source,          # "user" | "boosted"
        "last_updated": time.time(),
    })

    # ── Refresh cached mean ────────────────────────────────────────────────
    _refresh_mean(data, label)

    save_prototypes(data)
    return True


def update_prototype(
    label: str,
    idx: int,
    embedding: List[float],
    alpha: float = 0.2,
    confidence: float = 0.5,
):
    """EMA-update an existing prototype vector and refresh the class mean."""
    data = load_prototypes()
    if label not in data or idx >= len(data[label].get("prototypes", [])):
        return

    proto     = data[label]["prototypes"][idx]
    old_vec   = proto["vector"]
    
    # Dimension safety check: prevent corrupting prototypes with mixed dimensions
    if len(old_vec) != len(embedding):
        print(f"WARNING: Skipping prototype update for '{label}' due to dimension mismatch "
              f"({len(old_vec)} vs {len(embedding)})")
        return

    new_vec   = [(1 - alpha) * p + alpha * e for p, e in zip(old_vec, embedding)]

    proto["vector"]       = new_vec
    proto["uses"]        += 1
    base_boost            = 0.15
    boost                 = base_boost * max(confidence, 0.3)
    proto["weight"]       = min(proto["weight"] + boost, 2.0)
    proto["last_updated"] = time.time()

    # ── Incremental Mean Update (Instant Learning) ─────────────────────────
    # Only reinforcement (alpha > 0) drifts the mean towards the sample.
    # Penalty (alpha < 0) pushes individual prototypes away but shouldn't 
    # poison the class mean with the negative sample.
    if alpha > 0:
        old_mean = data[label].get("mean_vector")
        count = data[label].get("total_count", 0)
        data[label]["mean_vector"] = _incremental_update_mean(old_mean, count, embedding)
        data[label]["total_count"] = count + 1

    save_prototypes(data)


def recompute_all_means():
    """
    Utility: recompute and persist mean_vector for every label.
    Call once after upgrading the store from an older schema or to 'un-poison'
    means that were corrupted by negative feedback.
    """
    data = load_prototypes()
    for label, info in data.items():
        # Rebuild mean from the clean diverse buffer
        protos = info.get("prototypes", [])
        info["mean_vector"] = _compute_mean_vector(protos)
        
        # Backfill total_count if it's unknown or legacy
        if info.get("total_count", 0) == 0:
            info["total_count"] = len(protos)

    save_prototypes(data)
    print(f"INFO: Sanitized and refreshed mean vectors for {len(data)} labels.")
