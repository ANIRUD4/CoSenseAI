"""
backend/utils/temporal_smoother.py

Temporal Smoothing for Edge-Device Inference
============================================
Maintains a sliding window of per-class similarity scores over the last N
inference frames.  The smoothed prediction is derived by exponential moving
average (EMA) over those scores, then picking the class with the highest
smoothed value.

Why this matters
----------------
- Single-frame decisions on a Pi camera stream can flicker between labels.
- EMA over N ≈ 5–10 frames is computationally free (no extra CNN calls) and
  eliminates most one-frame glitches.
- The smoother is *stateful*: call reset() when the scene changes or a new
  "infer session" starts (e.g. after a confirmed prediction).

Usage
-----
    smoother = TemporalSmoother(window=7, alpha=0.4)
    smoothed_label = smoother.update({"pen": 0.82, "pencil": 0.61})
"""

from collections import deque
from typing import Dict, Optional


# ── Config ────────────────────────────────────────────────────────────────────

#: Number of frames in the sliding window.
SMOOTHING_WINDOW: int = 7

#: EMA decay factor.  Higher → more weight on recent frames.
#: 0.4 gives a half-life of ~2 frames (fast response, still smooth).
EMA_ALPHA: float = 0.4

#: Minimum frames before we trust the smoothed output.
MIN_FRAMES_FOR_DECISION: int = 3


# ── Core class ────────────────────────────────────────────────────────────────

class TemporalSmoother:
    """
    EMA-based sliding-window smoother for per-class similarity scores.

    Parameters
    ----------
    window : int
        Maximum number of past frames to keep in memory.
    alpha  : float
        EMA decay weight (0 < alpha ≤ 1).  Higher = faster response.
    """

    def __init__(
        self,
        window: int = SMOOTHING_WINDOW,
        alpha: float = EMA_ALPHA,
    ):
        self.window = window
        self.alpha = alpha
        self._history: deque = deque(maxlen=window)
        self._ema: Dict[str, float] = {}
        self._frame_count: int = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, scores: Dict[str, float]) -> Optional[str]:
        """
        Feed per-class similarity scores for the current frame.

        Parameters
        ----------
        scores : dict mapping label -> similarity_score (float in [0, 1])

        Returns
        -------
        Smoothed top label, or None if fewer than MIN_FRAMES_FOR_DECISION frames
        have been seen (too early to trust the window).
        """
        self._history.append(scores)
        self._frame_count += 1

        # Update EMA for each class seen in this frame
        all_labels = set(self._ema) | set(scores)
        for label in all_labels:
            current_score = scores.get(label, 0.0)
            if label in self._ema:
                self._ema[label] = (
                    self.alpha * current_score
                    + (1.0 - self.alpha) * self._ema[label]
                )
            else:
                # First time seeing this label: seed EMA at its current value
                self._ema[label] = current_score

        if self._frame_count < MIN_FRAMES_FOR_DECISION:
            return None  # not enough data yet

        # Return the label with the highest EMA score
        best = max(self._ema, key=lambda l: self._ema[l])
        return best if self._ema[best] > 0 else None

    def smoothed_scores(self) -> Dict[str, float]:
        """Return the current EMA scores for all known labels."""
        return dict(self._ema)

    def reset(self):
        """
        Clear all history.  Call after a confirmed prediction or scene change
        so the next session starts fresh.
        """
        self._history.clear()
        self._ema.clear()
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def is_ready(self) -> bool:
        """True once the window has enough frames to be trusted."""
        return self._frame_count >= MIN_FRAMES_FOR_DECISION


# ── Module-level singleton ─────────────────────────────────────────────────────
# infer.py imports this.  A single smoother persists across requests so that
# consecutive /infer calls from the same live camera stream share history.

_GLOBAL_SMOOTHER = TemporalSmoother()


def get_smoother() -> TemporalSmoother:
    """Return the module-level singleton smoother."""
    return _GLOBAL_SMOOTHER
