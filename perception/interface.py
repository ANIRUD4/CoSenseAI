"""
perception/interface.py

Public facade for the perception layer.
Exposes `get_embedding()` and `EMBEDDING_DIM` so callers never depend on
internal engine details.
"""

import cv2
import numpy as np
from perception.embedding_engine import EmbeddingEngine, CLIP_EMBEDDING_DIM
from perception.preprocessor import Preprocessor

# ── Singleton instances (avoids re-loading the heavy CLIP model on every call) ─
_ENGINE: EmbeddingEngine | None = None
_PREPROCESSOR: Preprocessor | None = None


def _get_engine() -> EmbeddingEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = EmbeddingEngine()
    return _ENGINE


def _get_preprocessor() -> Preprocessor:
    global _PREPROCESSOR
    if _PREPROCESSOR is None:
        _PREPROCESSOR = Preprocessor()
    return _PREPROCESSOR


# Convenience constant: dimension of the active embedding.
# Callers (e.g. learning/interface.py) should import this instead of
# hard-coding a number so that changing the engine propagates automatically.
EMBEDDING_DIM: int = CLIP_EMBEDDING_DIM   # 512 for CLIP ViT-B/32


def get_embedding(
    image_frame: np.ndarray,
    use_center_roi: bool   = False,
    use_saliency_roi: bool = False,
    use_focus_roi: bool    = False,
    use_edge_roi: bool     = False,
    manual_bbox: dict      = None,
) -> dict:
    """
    Convert a single image frame into a fixed-length embedding vector.

    Parameters
    ----------
    image_frame     : np.ndarray  BGR image from camera / base64 decode.
    use_focus_roi   : Laplacian-variance focus crop (recommended).
                      Returns a 'focus_hint' if the frame is too blurry.
    use_edge_roi    : Canny edge-density crop (robust for fixed-focus webcams).
    use_saliency_roi: MOG2 motion-based crop.
    use_center_roi  : Fixed 60 % center crop.

    Priority: focus_roi > edge_roi > saliency_roi > center_roi > full frame

    Returns
    -------
    dict:
        "embedding"  – list[float], L2-normalised fixed-length vector
        "focus_hint" – str | None — UI hint when frame is blurry
        "roi_mode"   – str — which ROI mode was applied
        "engine"     – str — 'clip', 'tflite', or 'simple'
    """
    engine      = _get_engine()
    preprocessor = _get_preprocessor()

    result = preprocessor.process(
        image_frame,
        use_focus_roi=use_focus_roi,
        use_edge_roi=use_edge_roi,
        use_saliency_roi=use_saliency_roi,
        use_center_roi=use_center_roi,
        manual_bbox=manual_bbox,
    )

    embedding = engine.get_embedding(result["frame"], normalize=True)

    return {
        "embedding":  list(embedding),
        "focus_hint": result.get("focus_hint"),
        "roi_mode":   result.get("roi_mode", "full_frame"),
        "engine":     engine.active_engine,
    }


def get_engine_info() -> dict:
    """Return metadata about the currently active embedding engine."""
    engine = _get_engine()
    return {
        "engine":        engine.active_engine,
        "embedding_dim": EMBEDDING_DIM,
        "clip_available": engine.active_engine == "clip",
    }


def get_embedding_from_image(image_frame: np.ndarray) -> list | None:
    """
    Convenience wrapper used by the LLM augmentation service.
    Returns a plain List[float] embedding from any OpenCV BGR image,
    or None if embedding fails.
    """
    try:
        result = get_embedding(image_frame, use_focus_roi=False)
        return result["embedding"]
    except Exception as e:
        print(f"get_embedding_from_image failed: {e}")
        return None
