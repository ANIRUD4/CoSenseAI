# learning/confidence.py
#
# NOTE: This module applies ONLY to the optional SGD refinement layer
# (IncrementalLearner.ENABLE_SGD_REFINEMENT = True).
#
# Core object recognition uses class-aware *adaptive* thresholds computed from
# the intra-class spread of stored prototypes (see backend/utils/threshold.py).
# The constant here is a last-resort safety net — NOT the primary decision gate.

# SGD-layer fallback threshold (used only when SGD refinement is enabled)
SGD_CONFIDENCE_FLOOR = 0.50


def is_confident(probability: float) -> bool:
    """Returns True if the SGD-layer probability clears the floor threshold."""
    return probability >= SGD_CONFIDENCE_FLOOR
