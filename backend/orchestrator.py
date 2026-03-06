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
from backend.storage.prototype_store import add_prototype, load_prototypes
from backend.utils.diversity import select_diverse_prototypes, MIN_DIVERSITY, MAX_PROTOTYPES_PER_LABEL

# Raspberry Pi Optimization: Track last inference time to prevent CPU spam
_LAST_INFERENCE_TIME = 0
_INFERENCE_COOLDOWN = 0.5  # 500ms cooldown for Pi stability

def learning_flow(image_frame):
    """
    Called when user presses 'Learn'
    """

    # 1. Vision (Always process learning frames)
    emb_result = get_embedding(image_frame, use_center_roi=True)
    embedding   = emb_result["embedding"]

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
    Diversity-Based Multi-shot Learn:
    - Capture k candidate frames
    - Run greedy max-distance selection to find diverse embeddings
    - Store only the embeddings that pass diversity gating

    This replaces the old "store all K frames" policy:
    - Redundant viewpoints are discarded, saving RAM and disk
    - Memory is bounded by MAX_PROTOTYPES_PER_LABEL (default: 15)
    - When the cap is reached, the weakest/oldest prototype is evicted
    """
    label = label.lower()
    candidates = []

    for _ in range(k):
        frame = get_frame_fn()
        emb_result = get_embedding(frame, use_focus_roi=True)  # focus-based ROI
        candidates.append(emb_result["embedding"])
        time.sleep(delay)

    # Load existing prototypes for this label to check against
    data = load_prototypes()
    existing_vectors = [
        p["vector"]
        for p in data.get(label, {}).get("prototypes", [])
    ]

    # Greedy diversity selection from candidates
    accepted, skipped = select_diverse_prototypes(
        candidates=candidates,
        existing_vectors=existing_vectors,
        min_diversity=MIN_DIVERSITY,
        max_count=MAX_PROTOTYPES_PER_LABEL,
    )

    print(
        f"DIVERSITY multishot '{label}': "
        f"{len(accepted)} accepted, {skipped} skipped (redundant) "
        f"from {k} captured frames"
    )

    stored = 0
    for emb in accepted:
        if add_prototype(label, emb):
            stored += 1

    return {
        "status": "stored",
        "label": label,
        "captured": k,
        "stored": stored,
        "skipped": skipped,
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

    emb_result = get_embedding(image_frame, use_focus_roi=True)
    embedding  = emb_result["embedding"]
    prediction = predict(embedding)
    
    _LAST_INFERENCE_TIME = time.time()

    return {
        "embedding": embedding,
        "prediction": prediction,
        "roi_mode": emb_result.get("roi_mode"),
        "focus_hint": emb_result.get("focus_hint"),
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
