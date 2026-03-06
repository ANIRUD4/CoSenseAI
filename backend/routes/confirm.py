from fastapi import APIRouter, HTTPException

from backend.schemas.confirmation import ConfirmationRequest
from backend.storage.prototype_store import (
    load_prototypes,
    update_prototype,
    add_prototype,
    save_prototypes
)
from backend.storage.negative_store import add_hard_negative
from backend.utils.similarity import compute_similarity
from backend.utils.threshold import GLOBAL_FALLBACK as _FALLBACK_THRESH
from backend.storage.metrics_store import log_event # Added for performance metrics

MAX_THRESHOLD_HINTS = 20  # cap on stored hints per class to bound JSON size


router = APIRouter(prefix="/confirm", tags=["Confirmation"])


@router.post("/")
def confirm_prediction(req: ConfirmationRequest):
    """
    Phase 4 Confirmation Logic (Improved HITL Learning)

    - If confirmed:
        Reinforce closest prototype (confidence-scaled)

    - If corrected:
        Targeted penalty on closest wrong prototype + add new one with inherited action
    """

    try:
        print(f"DEBUG: Received Confirmation Request: {req}")  # Debug Log

        # Get confidence (default 0.5 if not provided)
        confidence = req.confidence if req.confidence is not None else 0.5
        
        # -----------------------------
        # Validate embedding
        # -----------------------------
        if not req.embedding or len(req.embedding) == 0:
            print("DEBUG: Embedding missing or empty")
            raise HTTPException(
                status_code=400,
                detail="Embedding is required"
            )

        data = load_prototypes()

        predicted = (
            req.predicted_label.strip().lower()
            if req.predicted_label
            else ""
        )

        # =============================
        # ✅ CASE 1: CONFIRMED
        # =============================
        if req.confirmed:

            if not predicted:
                raise HTTPException(
                    status_code=400,
                    detail="predicted_label is required"
                )

            if predicted not in data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Label '{predicted}' not found"
                )

            protos = data[predicted]["prototypes"]

            if not protos:
                raise HTTPException(
                    status_code=404,
                    detail=f"No prototypes for '{predicted}'"
                )

            # 🔍 Find closest prototype
            best_idx = 0
            best_sim = -1

            for i, proto in enumerate(protos):

                sim = compute_similarity(
                    req.embedding,
                    proto["vector"]
                )

                if sim > best_sim:
                    best_sim = sim
                    best_idx = i

            # Reinforce closest prototype (confidence-scaled)
            update_prototype(predicted, best_idx, req.embedding, confidence=confidence)

            # Log metric event
            log_event(predicted, True, confidence)

            # ── Adaptive threshold hint: borderline confirmation widens threshold ─
            class_thresh = data[predicted].get("threshold_hints", {})
            computed_thresh = data[predicted].get("_cached_threshold", _FALLBACK_THRESH)
            if best_sim <= computed_thresh * 1.10:  # within 10% of threshold
                hints = class_thresh.setdefault("confirmations", [])
                hints.append(round(best_sim, 4))
                if len(hints) > MAX_THRESHOLD_HINTS:
                    hints[:] = hints[-MAX_THRESHOLD_HINTS:]
                data[predicted]["threshold_hints"] = class_thresh
                save_prototypes(data)
                print(
                    f"THRESHOLD HINT: borderline confirm for '{predicted}' "
                    f"sim={best_sim:.4f} (within 10% of threshold ~{computed_thresh:.3f})"
                )

            return {
                "status": "updated",
                "label": predicted,
                "mode": "reinforce",
                "prototype_index": best_idx,
                "similarity": round(best_sim, 4),
                "confidence_used": round(confidence, 4)
            }

        # =============================
        # ❌ CASE 2: CORRECTED
        # =============================

        if not req.corrected_label:
            print("DEBUG: corrected_label missing")
            raise HTTPException(
                status_code=400,
                detail="corrected_label is required when confirmed is false"
            )

        corrected = req.corrected_label.strip().lower()

        if not corrected:
            print("DEBUG: corrected_label is empty string")
            raise HTTPException(
                status_code=400,
                detail="corrected_label is empty"
            )

        # =============================
        # 🔥 TARGETED PENALTY: Only penalize the most responsible wrong prototype
        # =============================

        penalized_info = None

        if predicted in data:

            protos = data[predicted]["prototypes"]

            if protos:
                # 🎯 Find the closest prototype (the culprit)
                culprit_idx = 0
                culprit_sim = -1

                for i, proto in enumerate(protos):
                    sim = compute_similarity(req.embedding, proto["vector"])
                    if sim > culprit_sim:
                        culprit_sim = sim
                        culprit_idx = i

                # ⚡ Confidence-scaled penalty:
                # High confidence wrong prediction → stronger penalty
                # penalty_factor ranges from 0.80 (harsh) to 0.95 (mild)
                penalty_factor = 0.95 - (0.15 * confidence)
                old_weight = protos[culprit_idx]["weight"]
                protos[culprit_idx]["weight"] = max(
                    protos[culprit_idx]["weight"] * penalty_factor,
                    0.1
                )

                penalized_info = {
                    "penalized_label": predicted,
                    "penalized_index": culprit_idx,
                    "similarity_to_culprit": round(culprit_sim, 4),
                    "old_weight": round(old_weight, 4),
                    "new_weight": round(protos[culprit_idx]["weight"], 4),
                    "penalty_factor": round(penalty_factor, 4)
                }

                print(f"DEBUG: Targeted penalty on '{predicted}' proto[{culprit_idx}]: "
                    f"weight {old_weight:.3f} -> {protos[culprit_idx]['weight']:.3f} "
                    f"(factor={penalty_factor:.2f}, confidence={confidence:.2f})")

                # Save penalty update
                save_prototypes(data)

                # ── Hard-negative mining: record this embedding as a hard negative ──
                add_hard_negative(
                    label=predicted,
                    embedding=req.embedding,
                    confused_with=req.corrected_label,
                )

                # ── Adaptive threshold hint: this sim caused a FP -> shrink threshold ─
                hints = data[predicted].setdefault("threshold_hints", {})
                corrections = hints.setdefault("corrections", [])
                corrections.append(round(culprit_sim, 4))
                if len(corrections) > MAX_THRESHOLD_HINTS:
                    corrections[:] = corrections[-MAX_THRESHOLD_HINTS:]
                data[predicted]["threshold_hints"] = hints
                save_prototypes(data)

        # =============================
        # 🔁 ACTION INHERITANCE: Get action from existing prototypes of corrected label
        # =============================

        inherited_action = None
        data = load_prototypes()  # Reload after penalty save

        if corrected in data and data[corrected]["prototypes"]:
            # Inherit action from the first prototype that has one
            for proto in data[corrected]["prototypes"]:
                if proto.get("action"):
                    inherited_action = proto["action"]
                    break

            print(f"DEBUG: Inherited action '{inherited_action}' from existing '{corrected}' prototypes")

        # =============================
        # ✅ Add new correct prototype (with inherited action)
        # =============================

        add_prototype(corrected, req.embedding, inherited_action)

        # Log metric event (Correction)
        log_event(corrected, False, confidence)

        response = {
            "status": "updated",
            "label": corrected,
            "mode": "corrected",
            "action": "targeted_penalty_and_new_added",
            "inherited_action": inherited_action,
            "confidence_used": round(confidence, 4)
        }

        if penalized_info:
            response["penalty_details"] = penalized_info

        return response

    except HTTPException as he:
        print(f"CONFIRM 400 (HTTPException): {he.detail}")
        raise

    except Exception as e:
        import traceback
        print(f"CONFIRM 500 (Unhandled): {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Internal Error: {str(e)}")
