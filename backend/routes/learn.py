from fastapi import APIRouter, HTTPException

from backend.schemas.learning import LearningRequest
from backend.storage.prototype_store import add_prototype
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

    try:

        # Handle Base64 Image
        if req.image_base64:
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
                
                # Generate embedding
                # req.embedding = get_embedding(img)
                
                # Few-Shot Enhancement: Augment Data
                variations = augment_image(img)
                generated_embeddings = []
                
                for var_img in variations:
                    try:
                        emb = get_embedding(var_img, use_center_roi=True)
                        generated_embeddings.append(emb)
                    except Exception as embed_err:
                        print(f"Skipping augmented frame: {embed_err}")

                if not generated_embeddings:
                    raise ValueError("Could not generate any embeddings from image")
                
                # Assign to correct field for storage
                req.embeddings = generated_embeddings
                req.embedding = None # clear single shot slot to force multi-path

            except Exception as e:
                 raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")

        stored = 0

        # ✅ Multi-shot path (preferred)
        if req.embeddings and isinstance(req.embeddings, list) and len(req.embeddings) >= 2:

            for emb in req.embeddings:

                if not isinstance(emb, list):
                    raise ValueError("Embedding is not a list")

                if any(not isinstance(x, (int, float)) for x in emb):
                    raise ValueError("Embedding contains non-numeric values")

                if not emb or len(emb) == 0:
                    raise ValueError("Empty embedding in embeddings list")

                add_prototype(label, emb, req.action)
                stored += 1

            mode = "multi"

        # ✅ Single-shot fallback
        elif req.embedding:

            if not req.embedding or len(req.embedding) == 0:
                raise ValueError("Empty embedding")

            add_prototype(label, req.embedding, req.action)
            stored = 1
            mode = "single"

        else:
            raise HTTPException(
                status_code=400,
                detail="Provide 'embedding' (single) or 'embeddings' (multi-shot)"
            )

        return {
            "status": "stored",
            "label": label,
            "prototypes_added": stored,
            "mode": mode
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
