import cv2
import numpy as np
from perception.embedding_engine import EmbeddingEngine    

from perception.preprocessor import Preprocessor

# Raspberry Pi Optimization: Persistent engine instance to avoid reloading model
_ENGINE = None
_PREPROCESSOR = None

def get_embedding(image_frame, use_center_roi=False) -> list[float]:
    """
    Convert a single image frame into a fixed-length embedding vector.
    Uses a singleton EmbeddingEngine to optimize performance.

    Parameters:
        image_frame (np.ndarray):
            A single image frame captured from the camera (BGR format).
        use_center_roi (bool):
            Whether to extract the central area before embedding.

    Returns:
        list[float]:
            A fixed-length list of floats representing the visual embedding.
            Length is always constant across inputs.
    """
    global _ENGINE, _PREPROCESSOR
    if _ENGINE is None:
        _ENGINE = EmbeddingEngine()
    if _PREPROCESSOR is None:
        _PREPROCESSOR = Preprocessor()
        
    processed_frame = _PREPROCESSOR.process(image_frame, use_center_roi=use_center_roi)
        
    embedding = _ENGINE.get_embedding(processed_frame)
    return list(embedding)

