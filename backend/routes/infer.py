from fastapi import APIRouter

from backend.schemas.inference import InferRequest
from backend.storage.prototype_store import (
    load_prototypes,
    save_prototypes
)
from backend.utils.similarity import compute_similarity
from backend.utils.confidence import softmax
from backend.utils.drift import prune_prototypes
from backend.adapters import get_embedding
import base64
import numpy as np
import cv2
from fastapi import HTTPException


router = APIRouter(prefix="/infer", tags=["Inference"])


# ---------- Thresholds ----------
CONF_THRESHOLD = 0.50      # relative confidence
MARGIN_THRESHOLD = 0.15    # top1 - top2
SIM_THRESHOLD = 0.60       # absolute similarity - LOWERED for testing
# -------------------------------


@router.post("/")
def infer_object(req: InferRequest):

    # Handle Base64 Image -> Embedding
    if req.image_base64 and not req.embedding:
        try:
            if "," in req.image_base64:
                _, encoded = req.image_base64.split(",", 1)
            else:
                encoded = req.image_base64
            
            nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")
            
            req.embedding = get_embedding(img, use_center_roi=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")
    
    if not req.embedding:
         raise HTTPException(status_code=400, detail="No embedding or image provided")

    # =============================
    # 0️⃣ Load + prune drifted data
    # =============================
    prototypes = load_prototypes()

    if not prototypes:
        return {
            "message": "No knowledge available. Please teach me first.",
            "candidates": [],
            "decision": "empty"
        }

    # 🔥 Phase 3: remove weak / old memories
    prototypes = prune_prototypes(prototypes)
    save_prototypes(prototypes)

    labels = []
    sims = []
    actions_map = {}

    # =============================
    # 1️⃣ Compute best weighted similarity per label
    # =============================
    for label, info in prototypes.items():

        protos = info.get("prototypes", [])

        if not protos:
            continue

        best_sim = -1.0
        best_action = None

        # compare against all prototypes
        for p in protos:

            vector = p["vector"]
            weight = p.get("weight", 1.0)

            sim = compute_similarity(req.embedding, vector)

            # 🔥 Phase 3: weighted similarity
            weighted_sim = sim * weight

            if weighted_sim > best_sim:
                best_sim = weighted_sim
                best_action = p.get("action")
        
        print(f"DEBUG: Label '{label}' Best Sim: {best_sim}")  # Debug log

        if best_sim < 0:
            continue

        labels.append(label)
        sims.append(best_sim)
        actions_map[label] = best_action

    if not sims:
        return {
            "message": "No valid prototypes found.",
            "candidates": [],
            "decision": "empty"
        }

    # =============================
    # 2️⃣ Calibrate confidence
    # =============================
    confs = softmax(sims, temperature=0.05)

    # =============================
    # 3️⃣ Build candidate list
    # =============================
    candidates = []

    for i, label in enumerate(labels):

        proto_count = len(
            prototypes[label].get("prototypes", [])
        )

        candidates.append({
            "id": label,
            "label": label,
            "action": actions_map.get(label),  # ✅ Added Action

            # debug
            "similarity": round(float(sims[i]), 4),

            # calibrated confidence
            "confidence": round(float(confs[i]), 4),

            # how many memories exist
            "samples": proto_count
        })

    # =============================
    # 4️⃣ Sort by confidence
    # =============================
    candidates.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    # =============================
    # 5️⃣ Compute margin
    # =============================
    top1 = candidates[0]["confidence"]
    top1_sim = candidates[0]["similarity"]

    top2 = (
        candidates[1]["confidence"]
        if len(candidates) > 1
        else 0.0
    )

    gap = round(top1 - top2, 4)

    # =============================
    # 6️⃣ Open-set rejection
    # =============================
    if top1_sim < SIM_THRESHOLD:

        return {
            "message": "Unknown object. Please teach me.",
            "candidates": candidates[:3],
            "decision": "unknown_open_set",

            "top1": top1,
            "top2": top2,
            "gap": gap,
            "similarity": top1_sim,
            "embedding": req.embedding
        }

    # =============================
    # 7️⃣ Low confidence
    # =============================
    if top1 < CONF_THRESHOLD:

        return {
            "message": "Low confidence. Please teach me.",
            "candidates": candidates[:3],
            "decision": "unknown_low_confidence",

            "top1": top1,
            "top2": top2,
            "gap": gap,
            "embedding": req.embedding
        }

    # =============================
    # 8️⃣ Ambiguous
    # =============================
    if gap < MARGIN_THRESHOLD:

        return {
            "message": "Ambiguous result. Please confirm.",
            "candidates": candidates[:3],
            "decision": "unknown_ambiguous",

            "top1": top1,
            "top2": top2,
            "gap": gap,
            "embedding": req.embedding
        }

    # =============================
    # 9️⃣ Confident
    # =============================
    return {
        "message": "I think it might be one of these. Please confirm.",
        "candidates": candidates[:5],
        "decision": "confident",

        "top1": top1,
        "top2": top2,
        "gap": gap,
        "embedding": req.embedding
    }
