from fastapi import APIRouter, HTTPException

from backend.schemas.inference import InferRequest
from backend.storage.prototype_store import (
    load_prototypes,
    save_prototypes,
    MIN_FOR_MEAN,
)
from backend.storage.negative_store import get_negative_vectors
from backend.utils.similarity import compute_similarity
from backend.utils.confidence import softmax
from backend.utils.drift import prune_prototypes
from backend.utils.threshold import (
    compute_class_threshold,
    FLOOR as SIM_FLOOR,
    GLOBAL_FALLBACK as SIM_FALLBACK,
)
from backend.utils.temporal_smoother import get_smoother
from backend.adapters import get_embedding
from learning.tflite_classifier import (
    get_classifier,
    MIN_SAMPLES_FOR_TFLITE,
)
import base64
import numpy as np
import cv2

# Scale factor for hard-negative similarity penalty.
# final_sim = best_sim - NEGATIVE_PENALTY * max(0, best_neg_sim - best_sim)
NEGATIVE_PENALTY_SCALE: float = 0.30


router = APIRouter(prefix="/infer", tags=["Inference"])


# ---------- Fixed thresholds (non-similarity) ----------
CONF_THRESHOLD   = 0.50    # relative softmax confidence
MARGIN_THRESHOLD = 0.15    # top1 - top2 margin
#
# Similarity thresholds are fully data-driven and per-class.
# SIM_FLOOR is the absolute minimum (no class goes below this).
# SIM_FALLBACK is used only when a class has 0–1 prototypes (safety net).
# -------------------------------------------------------


# ── Engine-status endpoint ─────────────────────────────────────────────────

@router.get("/engine-status")
def engine_status():
    """
    Returns metadata about the active embedding and classifier engines.
    Useful for diagnostics and the frontend status bar.
    """
    try:
        from perception.interface import get_engine_info, EMBEDDING_DIM
        info = get_engine_info()
    except Exception:
        info = {"engine": "unknown", "embedding_dim": 512, "clip_available": False}

    clf = get_classifier()
    return {
        "embedding_engine":   info.get("engine", "unknown"),
        "embedding_dim":      info.get("embedding_dim", 512),
        "clip_available":     info.get("clip_available", False),
        "tflite_classifier":  clf.available,
        "tflite_model_path":  clf.model_path if clf.available else None,
        "min_samples_for_tflite": MIN_SAMPLES_FOR_TFLITE,
    }


# ── Main inference endpoint ────────────────────────────────────────────────

@router.post("/")
def infer_object(req: InferRequest):

    # ── Handle Base64 Image → Embedding ───────────────────────────────────
    _engine_used = "unknown"

    if req.image_base64 and not req.embedding:
        try:
            if "," in req.image_base64:
                _, encoded = req.image_base64.split(",", 1)
            else:
                encoded = req.image_base64

            nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
            img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image")

            emb_result = get_embedding(img, use_focus_roi=True)
            req.embedding = emb_result["embedding"]
            _engine_used  = emb_result.get("engine", "unknown")

            _focus_hint = emb_result.get("focus_hint")
            if _focus_hint:
                return {
                    "message":    _focus_hint,
                    "decision":   "focus_needed",
                    "focus_hint": _focus_hint,
                    "embedding":  None,
                }

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")

    if not req.embedding:
        raise HTTPException(status_code=400, detail="No embedding or image provided")

    # =====================================================================
    # 0️⃣  Load + prune drifted data
    # =====================================================================
    prototypes = load_prototypes()

    if not prototypes:
        return {
            "message":    "No knowledge available. Please teach me first.",
            "candidates": [],
            "decision":   "empty",
        }

    prototypes = prune_prototypes(prototypes)
    save_prototypes(prototypes)

    labels          = []
    sims            = []
    actions_map     = {}
    class_thresholds = {}
    proto_counts    = {}

    # =====================================================================
    # 1️⃣  Compute best similarity per label
    #
    #   Strategy:
    #     • ≥ MIN_FOR_MEAN (3) prototypes  →  similarity to the cached mean
    #       vector (class centroid).  This is the "prototype-mean" approach
    #       recommended by the research — fast and more representative than
    #       picking the single closest stored example.
    #     • < MIN_FOR_MEAN prototypes      →  best-individual-prototype score
    #       (not enough data to trust the mean yet).
    # =====================================================================
    for label, info in prototypes.items():

        protos = info.get("prototypes", [])
        if not protos:
            continue

        num_protos = len(protos)
        mean_vec   = info.get("mean_vector")          # cached centroid

        if num_protos >= MIN_FOR_MEAN and mean_vec is not None:
            # ── Mean-vector path (centroid matching) ───────────────────────
            best_sim    = compute_similarity(req.embedding, mean_vec)
            best_action = None  # mean vector has no single action
            score_mode  = "mean"
        else:
            # ── Individual-prototype path ──────────────────────────────────
            best_sim    = -1.0
            best_action = None
            score_mode  = "individual"

            for p in protos:
                vector = p["vector"]
                weight = p.get("weight", 1.0)
                sim    = compute_similarity(req.embedding, vector) * weight
                if sim > best_sim:
                    best_sim    = sim
                    best_action = p.get("action")

        print(
            f"DEBUG: Label '{label}' "
            f"sim={best_sim:.4f} ({score_mode}, {num_protos} protos)"
        )

        if best_sim < 0:
            continue

        # ── Hard-negative penalty ──────────────────────────────────────────
        neg_vecs = get_negative_vectors(label)
        if neg_vecs:
            # Filter vectors that match the input dimension to prevent crashes
            valid_neg_vecs = [
                nv for nv in neg_vecs 
                if len(req.embedding) == len(nv)
            ]
            
            if len(valid_neg_vecs) < len(neg_vecs):
                print(f"WARNING: Skipped {len(neg_vecs) - len(valid_neg_vecs)} stale negatives for '{label}' (dim mismatch)")

            if valid_neg_vecs:
                best_neg_sim = max(
                    compute_similarity(req.embedding, nv) for nv in valid_neg_vecs
                )
                if best_neg_sim > best_sim:
                    penalty  = NEGATIVE_PENALTY_SCALE * (best_neg_sim - best_sim)
                    best_sim = max(0.0, best_sim - penalty)
                    print(
                        f"HARD-NEG penalty for '{label}': "
                        f"neg_sim={best_neg_sim:.4f} → penalised sim={best_sim:.4f}"
                    )

        labels.append(label)
        sims.append(best_sim)
        actions_map[label]      = best_action
        class_thresholds[label] = compute_class_threshold(protos)
        proto_counts[label]     = num_protos

    if not sims:
        return {
            "message":    "No valid prototypes found.",
            "candidates": [],
            "decision":   "empty",
        }

    # =====================================================================
    # 2️⃣  Calibrate confidence (softmax over similarities)
    # =====================================================================
    confs = softmax(sims, temperature=0.05)

    # =====================================================================
    # 3️⃣  Build candidate list
    # =====================================================================
    candidates = []
    for i, label in enumerate(labels):
        candidates.append({
            "id":         label,
            "label":      label,
            "action":     actions_map.get(label),
            "similarity": round(float(sims[i]), 4),
            "confidence": round(float(confs[i]), 4),
            "samples":    proto_counts.get(label, 0),
        })

    # =====================================================================
    # 4️⃣  Sort by confidence
    # =====================================================================
    candidates.sort(key=lambda x: x["confidence"], reverse=True)

    # =====================================================================
    # 4b️⃣  Temporal smoothing
    # =====================================================================
    raw_scores    = {c["label"]: c["similarity"] for c in candidates}
    smoother      = get_smoother()
    smoothed_label = smoother.update(raw_scores)

    # =====================================================================
    # 4c️⃣  TFLite hybrid path (optional — only when model is loaded)
    #
    #   If the top prototype-similarity candidate has ≥ MIN_SAMPLES_FOR_TFLITE
    #   examples, run the fine-tuned TFLite classifier.  If it returns a
    #   confident result, prefer it as the final answer.
    # =====================================================================
    tflite_result = None
    top_count     = proto_counts.get(candidates[0]["label"], 0)

    if top_count >= MIN_SAMPLES_FOR_TFLITE:
        clf = get_classifier()
        if clf.available and req.image_base64:
            # Decode image again (we already have the embedding but TFLite
            # needs a raw image tensor, not the CLIP embedding).
            try:
                if "," in req.image_base64:
                    _, enc = req.image_base64.split(",", 1)
                else:
                    enc = req.image_base64
                nparr  = np.frombuffer(base64.b64decode(enc), np.uint8)
                img    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                img_f  = cv2.resize(img, (224, 224)).astype(np.float32) / 255.0
                # Build label_map from current prototype store order
                label_map = {i: lbl for i, lbl in enumerate(sorted(prototypes.keys()))}
                tflite_result = clf.predict(img_f, label_map)
            except Exception as tf_err:
                print(f"WARNING: TFLite inference failed: {tf_err}")

    # =====================================================================
    # 5️⃣  Compute margin
    # =====================================================================
    top1     = candidates[0]["confidence"]
    top1_sim = candidates[0]["similarity"]
    top2     = candidates[1]["confidence"] if len(candidates) > 1 else 0.0
    gap      = round(top1 - top2, 4)

    # =====================================================================
    # 6️⃣  Open-set rejection (per-class adaptive threshold)
    # =====================================================================
    top_label          = candidates[0]["label"]
    class_sim_threshold = class_thresholds.get(top_label, SIM_FALLBACK)
    prototypes[top_label]["_cached_threshold"] = class_sim_threshold

    print(
        f"ADAPTIVE THRESHOLD: label='{top_label}' "
        f"threshold={class_sim_threshold:.3f} sim={top1_sim:.4f}"
    )

    uncertainty_margin = class_sim_threshold * 0.10
    uncertainty_signal = (
        "high" if top1_sim <= class_sim_threshold + uncertainty_margin else "low"
    )
    ask_confirm = (uncertainty_signal == "high")

    if top1_sim < class_sim_threshold:
        return {
            "message":           "Unknown object. Please teach me.",
            "candidates":        candidates[:3],
            "decision":          "unknown_open_set",
            "top1":              top1,
            "top2":              top2,
            "gap":               gap,
            "similarity":        top1_sim,
            "class_threshold":   class_sim_threshold,
            "uncertainty_signal": uncertainty_signal,
            "ask_confirm":       ask_confirm,
            "smoothed_label":    smoothed_label,
            "embedding":         req.embedding,
        }

    # =====================================================================
    # 6b️⃣  Single-class guard
    # =====================================================================
    if len(candidates) == 1:
        headroom_threshold = class_sim_threshold * 1.15
        if top1_sim < headroom_threshold:
            print(
                f"SINGLE-CLASS GUARD: only 1 class known, "
                f"top1_sim={top1_sim:.4f} < headroom={headroom_threshold:.4f} → unknown"
            )
            return {
                "message":           "Unknown object. Please teach me.",
                "candidates":        candidates[:3],
                "decision":          "unknown_single_class",
                "top1":              top1,
                "top2":              top2,
                "gap":               gap,
                "similarity":        top1_sim,
                "class_threshold":   class_sim_threshold,
                "uncertainty_signal": "high",
                "ask_confirm":       True,
                "smoothed_label":    smoothed_label,
                "embedding":         req.embedding,
            }

    # =====================================================================
    # 7️⃣  Low confidence
    # =====================================================================
    if top1 < CONF_THRESHOLD:
        return {
            "message":           "Low confidence. Please teach me.",
            "candidates":        candidates[:3],
            "decision":          "unknown_low_confidence",
            "top1":              top1,
            "top2":              top2,
            "gap":               gap,
            "uncertainty_signal": uncertainty_signal,
            "ask_confirm":       ask_confirm,
            "smoothed_label":    smoothed_label,
            "embedding":         req.embedding,
        }

    # =====================================================================
    # 8️⃣  Ambiguous
    # =====================================================================
    if gap < MARGIN_THRESHOLD:
        return {
            "message":           "Ambiguous result. Please confirm.",
            "candidates":        candidates[:3],
            "decision":          "unknown_ambiguous",
            "top1":              top1,
            "top2":              top2,
            "gap":               gap,
            "uncertainty_signal": uncertainty_signal,
            "ask_confirm":       True,
            "smoothed_label":    smoothed_label,
            "embedding":         req.embedding,
        }

    # =====================================================================
    # 9️⃣  Confident — apply TFLite override if available
    # =====================================================================
    smoother.reset()

    # =====================================================================
    # 9️⃣  Confident — Semantic Ensembling (CLIP + TFLite)
    # =====================================================================
    smoother.reset()

    final_label = top_label
    final_engine = _engine_used
    
    # If TFLite gave a result, we perform a weighted ensemble:
    # final_weight = (w_clip * clip_sim + w_tflite * tflite_prob)
    if tflite_result is not None:
        tflite_label = tflite_result["label"]
        tflite_conf  = tflite_result["confidence"]
        
        # Scenario A: Engines agree on the label
        if tflite_label == top_label:
            print(f"ENSEMBLE: Engines agree on '{top_label}'. Boosting confidence.")
            # Boost the top1 confidence because both engines agree
            candidates[0]["confidence"] = min(1.0, candidates[0]["confidence"] * 1.15)
        
        # Scenario B: TFLite is VERY confident but disagrees with CLIP
        elif tflite_conf > 0.85:
            print(f"ENSEMBLE: TFLite extremely confident in '{tflite_label}'. Overriding CLIP.")
            final_label = tflite_label
            final_engine = "tflite_classifier_ensemble"
            
        # Scenario C: Engines disagree, but TFLite is only moderately confident
        else:
            print(f"ENSEMBLE: Engines disagree ('{top_label}' vs '{tflite_label}'). Sticking with CLIP (semantic).")

    return {
        "message":    "I think it might be one of these. Please confirm.",
        "candidates": candidates[:5],
        "decision":   "confident",

        "top1":              candidates[0]["confidence"],
        "top2":              top2,
        "gap":               gap,
        "uncertainty_signal": uncertainty_signal,
        "ask_confirm":       ask_confirm,
        "smoothed_label":    smoothed_label,
        "root_label":        top_label, # original CLIP top label
        "embedding":         req.embedding,

        # Hybrid result metadata
        "final_label":       final_label,
        "embedding_engine":  final_engine,
        "tflite_override":   tflite_result is not None and final_label != top_label,
    }
