"""
backend/utils/drift.py

Memory Pruning Policy (4-Tier)
================================
Runs at inference time (infer.py) to keep prototype memory healthy on an
edge device.

Tier 0 – Intra-class near-duplicate removal
    Cosine sim >= NEAR_DUP_SIM -> near-duplicate. Keep higher-weight one.

Tier 1 – Stale removal
    Prototypes older than MAX_AGE seconds are evicted.

Tier 2 – Weak removal
    Prototypes with weight < MIN_WEIGHT AND uses < 2 are evicted.

Tier 3 – Per-class overflow cap
    Excess prototypes beyond MAX_PROTOTYPES_PER_LABEL are removed (keep best).

Global budget
    If total across ALL classes > GLOBAL_BUDGET, prune globally weakest by
    composite LFU score until the budget is met.
"""

import time
import numpy as np
from backend.utils.diversity import MAX_PROTOTYPES_PER_LABEL

MAX_AGE       = 7 * 24 * 3600   # 7 days
MIN_WEIGHT    = 0.3
NEAR_DUP_SIM  = 0.95            # cosine sim above this -> near-duplicate
GLOBAL_BUDGET = 2_000           # max total prototypes across all classes


def _cosine_sim(a, b) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _lfu_score(p, now: float) -> float:
    """Lower score -> better eviction candidate."""
    weight = p.get("weight", 1.0)
    uses   = p.get("uses", 1)
    age    = now - p.get("last_updated", now)
    return (weight * uses) / max(age + 1, 1)


def _tier0_dedup(protos: list) -> list:
    """
    Remove near-duplicate prototypes within a class.
    For each cosine-similar pair, keep the higher-weight prototype.
    """
    if len(protos) < 2:
        return protos

    keep = [True] * len(protos)

    for i in range(len(protos)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(protos)):
            if not keep[j]:
                continue
            sim = _cosine_sim(protos[i]["vector"], protos[j]["vector"])
            if sim >= NEAR_DUP_SIM:
                if protos[i].get("weight", 1.0) >= protos[j].get("weight", 1.0):
                    keep[j] = False
                else:
                    keep[i] = False
                    break  # i dropped; advance outer loop

    return [p for k, p in zip(keep, protos) if k]


def prune_prototypes(data: dict) -> dict:
    """
    Four-tier memory policy. Returns the pruned data dict.
    """
    now = time.time()

    for label in list(data.keys()):
        protos = data[label].get("prototypes", [])
        before_count = len(protos)

        # Tier 0: Near-duplicate removal
        protos = _tier0_dedup(protos)

        # Tier 1 & 2: Stale & Weak
        protos = [
            p for p in protos
            if (
                (p.get("weight", 1.0) >= MIN_WEIGHT or p.get("uses", 1) >= 2)
                and (now - p.get("last_updated", now)) <= MAX_AGE
            )
        ]

        # Tier 3: Per-class overflow cap
        if len(protos) > MAX_PROTOTYPES_PER_LABEL:
            protos.sort(
                key=lambda x: (x.get("weight", 1.0), x.get("last_updated", 0)),
                reverse=True,
            )
            protos = protos[:MAX_PROTOTYPES_PER_LABEL]

        after_count = len(protos)
        if before_count != after_count:
            print(f"DRIFT: Pruned '{label}' ({before_count} -> {after_count} prototypes)")

        if protos:
            data[label]["prototypes"] = protos
        else:
            print(f"DRIFT: Label '{label}' has no prototypes remaining -- deleted.")
            del data[label]

    # Global budget enforcement
    total = sum(len(v.get("prototypes", [])) for v in data.values())
    if total > GLOBAL_BUDGET:
        excess = total - GLOBAL_BUDGET
        candidates = []
        for label, info in data.items():
            for idx, p in enumerate(info.get("prototypes", [])):
                candidates.append((label, idx, _lfu_score(p, now)))
        candidates.sort(key=lambda x: x[2])  # weakest first
        to_remove = candidates[:excess]
        by_label: dict = {}
        for label, idx, _ in to_remove:
            by_label.setdefault(label, []).append(idx)
        for label, idxs in by_label.items():
            for idx in sorted(idxs, reverse=True):
                data[label]["prototypes"].pop(idx)
        print(f"DRIFT: Global budget exceeded -- removed {excess} prototypes globally.")

    return data
