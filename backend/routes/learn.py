from fastapi import APIRouter, HTTPException

from backend.schemas.learning import LearningRequest
from backend.storage.prototype_store import add_prototype, load_prototypes
from backend.storage.collector import save_collected_data
from backend.utils.diversity import select_diverse_prototypes
from backend.adapters import get_embedding
import base64
import numpy as np
import cv2


def augment_image(image: np.ndarray) -> list[np.ndarray]:
    """
    Generates variations of the input image to simulate different conditions:
    - Rotations (+/- 10 degrees)
    - Brightness changes (+/- 20%)
    - Gaussian noise
    """
    variations = [image]  # Always include original
    rows, cols, _ = image.shape

    # 1. Rotations
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
        rotated = cv2.warpAffine(image, M, (cols, rows))
        variations.append(rotated)

    # 2. Brightness
    # Convert to HSV, adjust V channel, convert back
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # Brighten
    v_bright = cv2.add(v, 40)
    final_bright = cv2.merge((h, s, v_bright))
    variations.append(cv2.cvtColor(final_bright, cv2.COLOR_HSV2BGR))

    # Darken
    v_dark = cv2.subtract(v, 40)
    final_dark = cv2.merge((h, s, v_dark))
    variations.append(cv2.cvtColor(final_dark, cv2.COLOR_HSV2BGR))

    # 3. Noise
    gaussian_noise = np.zeros(image.shape, dtype=np.uint8)
    cv2.randn(gaussian_noise, (0, 0, 0), (20, 20, 20))  # mean=0, std=20
    noisy_image = cv2.add(image, gaussian_noise)
    variations.append(noisy_image)

    return variations


router = APIRouter(prefix="/learn", tags=["Learning"])


@router.post("/commit")
def commit_learning(req: LearningRequest):
    """
    Supports:
    1) Single-shot learn  -> req.embedding
    2) Multi-shot learn   -> req.embeddings (preferred)

    Stores each embedding as a separate prototype.
    """

    # normalize label
    label = req.label.strip().lower()

    if not label:
        raise HTTPException(status_code=400, detail="Label is required")

    stored = 0
    skipped = 0
    mode = "single"
    image_mode = False

    try:

        # Handle Base64 Image
        if req.image_base64:
            image_mode = True
            try:
                # Remove header if present (e.g., "data:image/jpeg;base64,")
                if "," in req.image_base64:
                    _, encoded = req.image_base64.split(",", 1)
                else:
                    encoded = req.image_base64
                
                nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Failed to decode image from base64")

                # ── Data Collector (Save raw for future detector training) ──
                save_collected_data(img, label, req.roi_bbox)

                # Few-Shot Enhancement: Augment Data
                variations = augment_image(img)
                generated_embeddings = []

                for var_img in variations:
                    try:
                        emb_result = get_embedding(
                            var_img, 
                            use_focus_roi=not bool(req.roi_bbox),
                            manual_bbox=req.roi_bbox
                        )
                        generated_embeddings.append(emb_result["embedding"])

                    except Exception as embed_err:
                        print(f"Skipping augmented frame: {embed_err}")

                if not generated_embeddings:
                    raise ValueError("Could not generate any embeddings from image")

                # ── Diversity pre-filter on the augmented batch ──────────
                existing_protos = load_prototypes().get(label, {}).get("prototypes", [])
                existing_vectors = [p["vector"] for p in existing_protos]

                filtered, skipped_aug = select_diverse_prototypes(
                    candidates=generated_embeddings,
                    existing_vectors=existing_vectors,
                )
                print(
                    f"DIVERSITY (image batch): label='{label}' "
                    f"generated={len(generated_embeddings)}, "
                    f"accepted={len(filtered)}, skipped={skipped_aug}"
                )

                # Assign filtered embeddings for storage below
                req.embeddings = filtered
                req.embedding = None  # force multi-path
                skipped = skipped_aug  # Track redundancy from the augment batch

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"ERROR in commit_learning image processing: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")

        stored = 0

        # ✅ Multi-shot path (preferred)
        if req.embeddings and isinstance(req.embeddings, list) and len(req.embeddings) >= 1:

            stored = 0
            skipped = 0

            for emb in req.embeddings:

                if not isinstance(emb, list):
                    raise ValueError("Embedding is not a list")

                if any(not isinstance(x, (int, float)) for x in emb):
                    raise ValueError("Embedding contains non-numeric values")

                if not emb or len(emb) == 0:
                    raise ValueError("Empty embedding in embeddings list")

                accepted = add_prototype(label, emb, req.action)
                if accepted:
                    stored += 1
                else:
                    skipped += 1

            mode = "multi"
            print(
                f"LEARN /commit: label='{label}' stored={stored}, "
                f"skipped_as_redundant={skipped}"
            )

        # ✅ Single-shot fallback
        elif req.embedding:

            if not req.embedding or len(req.embedding) == 0:
                raise ValueError("Empty embedding")

            add_prototype(label, req.embedding, req.action)
            stored = 1
            mode = "single"

        # ✅ Graceful redundancy fallback
        elif image_mode:
            stored = 0
            mode = "multi"
            print(f"LEARN /commit: label='{label}' stored=0 (All frames redundant)")

        else:
            raise HTTPException(
                status_code=400,
                detail="Provide 'embedding' (single) or 'embeddings' (multi-shot)"
            )

        # ── Build wizard UX feedback ────────────────────────────────────────
        all_protos = load_prototypes().get(label, {}).get("prototypes", [])
        viewpoint_coverage = len(all_protos)
        RECOMMENDED_MIN = 5

        total_candidates = stored + skipped
        redundancy_rate  = round(
            (skipped / total_candidates * 100) if total_candidates > 0 else 0, 1
        )

        if redundancy_rate >= 80:
            wizard_message = (
                "All frames look nearly identical — please move or rotate the object "
                "to capture different viewpoints."
            )
        elif viewpoint_coverage < RECOMMENDED_MIN:
            wizard_message = (
                f"Good start! Try different angles — "
                f"{viewpoint_coverage}/{RECOMMENDED_MIN} diverse views captured."
            )
        else:
            wizard_message = (
                f"Capture complete. {viewpoint_coverage} diverse views stored for '{label}'."
            )

        return {
            "status": "stored",
            "label": label,
            "prototypes_added": stored,
            "mode": mode,
            # Wizard UX fields
            "viewpoint_coverage": viewpoint_coverage,
            "redundancy_rate": redundancy_rate,
            "wizard_message": wizard_message,
        }

    except HTTPException as he:
        print(f"LEARN 400 (HTTPException): {he.detail}")
        raise

    except Exception as e:
        import traceback
        print(f"LEARN 400 (Unhandled): {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Internal Error: {str(e)}")
