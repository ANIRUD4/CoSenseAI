"""
backend/utils/threshold.py

Class-Aware Adaptive Similarity Thresholds + Feedback Nudge
=============================================================
Computes a per-class rejection threshold from the intra-class spread of
stored prototypes, with an optional EMA nudge driven by user feedback.

Baseline algorithm
------------------
  >= 2 prototypes:  threshold = max(FLOOR, mean_pairwise_sim - K * std_pairwise_sim)
  1 prototype:      threshold = FLOOR
  0 prototypes:     threshold = GLOBAL_FALLBACK  (safety net)

Feedback nudge (3.3.2)
-----------------------
threshold_hints stored per-class:
    {"corrections": [sim_fp, ...], "confirmations": [sim_border, ...]}

  nudge = NUDGE_SCALE * (mean_confirm - mean_correct)
  final = clip(baseline + nudge, FLOOR, 1.0)

Corrections shrink the threshold; borderline confirmations widen it.
Nudge is capped at +/- MAX_NUDGE = 0.10 to keep the system stable.
"""

import numpy as np
from typing import List

# ── Tuning constants ──────────────────────────────────────────
K: float               = 2.0    # wider spread tolerance (demo: few prototypes per class)
FLOOR: float           = 0.45   # demo-safe minimum — still protects against junk matches
GLOBAL_FALLBACK: float = 0.60   # used when 0-1 prototypes exist; was 0.72 (too strict for demo)
NUDGE_SCALE: float     = 0.05
MAX_NUDGE: float       = 0.10


def _pairwise_cosine_sims(vectors: List[List[float]]) -> List[float]:
    """Return all unique pairwise cosine similarities for a list of vectors."""
    mats = [np.array(v, dtype=np.float32) for v in vectors]
    sims = []
    for i in range(len(mats)):
        ni = np.linalg.norm(mats[i])
        if ni == 0:
            continue
        for j in range(i + 1, len(mats)):
            nj = np.linalg.norm(mats[j])
            if nj == 0:
                continue
            sims.append(float(np.dot(mats[i], mats[j]) / (ni * nj)))
    return sims


def compute_class_threshold(
    prototypes: list,
    k: float = K,
    floor: float = FLOOR,
    fallback: float = GLOBAL_FALLBACK,
    threshold_hints: dict = None,
) -> float:
    """
    Compute the open-set rejection threshold for a single class.

    Parameters
    ----------
    prototypes       : list of prototype dicts (each has a "vector" key)
    k                : std-deviations below mean to set threshold
    floor            : absolute minimum threshold
    fallback         : threshold when < 2 prototypes exist
    threshold_hints  : optional {"corrections": [...], "confirmations": [...]}

    Returns
    -------
    float threshold in [floor, 1.0]
    """
    vectors = [p["vector"] for p in prototypes if "vector" in p]

    if len(vectors) < 2:
        # With 0 or 1 prototypes we have NO pairwise spread to work with.
        # We must be MORE conservative (higher bar), not lower.
        # Both cases use fallback (0.72) — the FLOOR (0.50) is only a safety
        # net for classes that have computed pairwise stats and are very spread.
        baseline = fallback
    else:
        sims = _pairwise_cosine_sims(vectors)
        if not sims:
            baseline = floor
        else:
            mean_sim = float(np.mean(sims))
            std_sim  = float(np.std(sims))
            baseline = float(max(floor, mean_sim - k * std_sim))

    # ── Feedback nudge ─────────────────────────────────────────
    if threshold_hints:
        corrections   = threshold_hints.get("corrections", [])
        confirmations = threshold_hints.get("confirmations", [])

        mean_corr    = float(np.mean(corrections))   if corrections   else None
        mean_confirm = float(np.mean(confirmations)) if confirmations else None

        nudge = 0.0
        if mean_corr is not None and mean_confirm is not None:
            nudge = NUDGE_SCALE * (mean_confirm - mean_corr)
        elif mean_corr is not None:
            nudge = -NUDGE_SCALE * 0.5   # only corrections: tighten slightly
        elif mean_confirm is not None:
            nudge = NUDGE_SCALE * 0.5    # only confirmations: loosen slightly

        nudge    = float(np.clip(nudge, -MAX_NUDGE, MAX_NUDGE))
        baseline = float(np.clip(baseline + nudge, floor, 1.0))

    return baseline


def compute_all_thresholds(prototypes_by_label: dict) -> dict:
    """
    Convenience wrapper: compute thresholds for all labels at once,
    passing per-class threshold_hints if present.

    Returns
    -------
    dict mapping label -> threshold
    """
    return {
        label: compute_class_threshold(
            info.get("prototypes", []),
            threshold_hints=info.get("threshold_hints"),
        )
        for label, info in prototypes_by_label.items()
    }
