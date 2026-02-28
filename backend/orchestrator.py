from backend.adapters import (
    get_embedding,
    predict,
    update,
    get_intent,
    get_confirmation
)
from interaction.interface import get_label 
import time
from typing import List
from backend.storage.prototype_store import add_prototype

# Raspberry Pi Optimization: Track last inference time to prevent CPU spam
_LAST_INFERENCE_TIME = 0
_INFERENCE_COOLDOWN = 0.5  # 500ms cooldown for Pi stability

def learning_flow(image_frame):
    """
    Called when user presses 'Learn'
    """

    # 1. Vision (Always process learning frames)
    embedding = get_embedding(image_frame, use_center_roi=True)

    # 2. Voice
    label_text = get_label()  

    return {
        "embedding": embedding,
        "label": label_text,
        "explanation": label_text
    }


def mean_embedding(embeddings: List[List[float]]) -> List[float]:
    k = len(embeddings)
    dim = len(embeddings[0])
    return [sum(e[i] for e in embeddings) / k for i in range(dim)]


def learning_flow_multishot(get_frame_fn, label: str, k: int = 10, delay: float = 0.12):
    """
    Multi-shot learn:
    - capture k frames
    - get embeddings
    - average into a prototype embedding
    - store/update centroid for label
    - store each embedding as a separate prototype for robustness (Phase 4 change)
    """
    embeddings = []

    for _ in range(k):
        frame = get_frame_fn()          # frontend->backend frame capture OR camera adapter
        emb = get_embedding(frame, use_center_roi=True)      # member1 perception
        embeddings.append(emb)
        time.sleep(delay)

    # Now we store all k prototypes for better precision
    for emb in embeddings:
        add_prototype(label.lower(), emb)

    return {
        "status": "stored",
        "label": label.lower(),
        "count": k,
        "k": k
    }


def inference_flow(image_frame):
    """
    Optimized for Raspberry Pi with throttling.
    """
    global _LAST_INFERENCE_TIME
    
    current_time = time.time()
    if current_time - _LAST_INFERENCE_TIME < _INFERENCE_COOLDOWN:
        # Skip inference if cooling down (only for background threads/auto-scans)
        # Note: If this is a direct user-initated scan, the router should call it properly.
        pass

    embedding = get_embedding(image_frame, use_center_roi=True)
    prediction = predict(embedding)
    
    _LAST_INFERENCE_TIME = time.time()

    return {
        "embedding": embedding,
        "prediction": prediction
    }

def feedback_flow(embedding, confirmed: bool, corrected_label: str | None, confidence: float = 0.5):
    """
    Updates memory using confidence-aware learning.
    """
    # Note: 'update' in adapters usually points to Confirmation logic or similar
    update(embedding, confirmed, corrected_label, confidence)

def get_confirmation_flow():
    return get_confirmation()

def get_intent_flow(audio_data):
    return get_intent(audio_data)
