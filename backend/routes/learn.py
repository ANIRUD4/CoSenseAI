from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.schemas.learning import LearningRequest
from backend.storage.prototype_store import add_prototype, load_prototypes
from backend.storage.collector import save_collected_data
from backend.utils.diversity import select_diverse_prototypes
from backend.adapters import get_embedding
from backend.llm_augment import augment_with_web_images
from interaction.gpio_controller import hw as _hw
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


def _run_llm_augmentation_bg(label: str, img: np.ndarray, max_web_images: int = 10):
    """
    Background task: fetch real images from the web via LLM augmentation
    and append their embeddings to the prototype store for the given label.
    Users are unaware of this; they see only their 3-7 captured samples.
    """
    from backend.storage.prototype_store import add_prototype
    from backend.utils.diversity import select_diverse_prototypes, MIN_DIVERSITY
    try:
        web_embeddings = augment_with_web_images(label, img, max_web_images=max_web_images)
        if not web_embeddings:
            return

        # Diversity-filter before adding
        existing_protos = load_prototypes().get(label, {}).get("prototypes", [])
        existing_vectors = [p["vector"] for p in existing_protos]
        accepted, skipped = select_diverse_prototypes(
            candidates=web_embeddings,
            existing_vectors=existing_vectors,
            min_diversity=MIN_DIVERSITY,
        )
        added = 0
        for emb in accepted:
            if add_prototype(label, emb, source="boosted"):
                added += 1
        print(
            f"LLM_AUGMENT BG: label='{label}' web_added={added} skipped={skipped}"
        )
    except Exception as e:
        import traceback
        print(f"LLM_AUGMENT BG error for label='{label}': {e}")
        traceback.print_exc()


@router.post("/commit")
def commit_learning(req: LearningRequest, background_tasks: BackgroundTasks):
    """
    Supports:
    1) Single-shot learn  -> req.embedding
    2) Multi-shot learn   -> req.embeddings (preferred)

    Stores each embedding as a separate prototype.
    After image-based learn, triggers LLM augmentation in the background.
    """

    # normalize label
    label = req.label.strip().lower()

    if not label:
        raise HTTPException(status_code=400, detail="Label is required")

    # Hardware: signal learning mode immediately (Green LED on, 1 short beep)
    _hw.set_learn_mode()

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

                # ── LLM background augmentation (DISABLED for demo accuracy) ──
                # Web-scraped images look different from Pi camera captures and
                # contaminate the prototype centroid.  Re-enable for general use.
                # background_tasks.add_task(_run_llm_augmentation_bg, label, img)

                # ── Data Collector (Save raw for future detector training) ──
                save_collected_data(img, label, req.roi_bbox)

                # Few-Shot Enhancement: Augment Data
                variations = augment_image(img)
                generated_embeddings = []

                for var_img in variations:
                    try:
                        emb_result = get_embedding(
                            var_img,
                            # Use center ROI for learning: user holds object steady,
                            # centre crop is more reproducible than focus/edge ROI.
                            use_center_roi=not bool(req.roi_bbox),
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

        # Hardware: success if we stored at least one prototype; otherwise
        # revert to infer mode (all frames were redundant — no new data added).
        if stored > 0:
            _hw.set_success()
        else:
            _hw.set_infer_mode()

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

import os
import glob
from fastapi.responses import FileResponse

@router.get("/images/{label}")
def get_label_images(label: str):
    """
    Returns a list of image filenames associated with a label from the collector.
    """
    from backend.storage.collector import COLLECTOR_DIR
    
    label = label.strip().lower()
    if not os.path.exists(COLLECTOR_DIR):
        return {"images": []}
        
    # Find all images for this label
    pattern = os.path.join(COLLECTOR_DIR, f"{label}_*.jpg")
    files = glob.glob(pattern)
    
    # Return just the filenames or relative paths
    filenames = [os.path.basename(f) for f in files]
    return {"images": filenames}


@router.get("/sync/{label}")
def sync_label(label: str):
    """
    Returns the current mean_vector (512-d centroid) and prototype stats for a label.
    Called by the companion app after a Boost job completes to confirm sync.
    The centroid alone is enough for inference — the Pi does not need all prototypes.
    """
    label = label.strip().lower()
    data = load_prototypes()
    label_data = data.get(label)

    if not label_data:
        raise HTTPException(status_code=404, detail=f"Label '{label}' not found in prototype store.")

    protos = label_data.get("prototypes", [])
    mean_vector = label_data.get("mean_vector")

    user_count    = sum(1 for p in protos if p.get("source", "user") == "user")
    boosted_count = sum(1 for p in protos if p.get("source") == "boosted")

    return {
        "label":         label,
        "mean_vector":   mean_vector,
        "total_count":   label_data.get("total_count", len(protos)),
        "buffer_count":  len(protos),
        "user_count":    user_count,
        "boosted_count": boosted_count,
        "has_mean":      mean_vector is not None,
    }

@router.get("/image/{filename}")
def get_image(filename: str):
    """
    Serves a specific collected image, with its ROI bounding box drawn if available.
    """
    from backend.storage.collector import COLLECTOR_DIR
    import json
    from fastapi.responses import Response
    
    file_path = os.path.join(COLLECTOR_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
        
    json_path = os.path.join(COLLECTOR_DIR, filename.split("?")[0].replace(".jpg", ".json"))
    
    try:
        if not os.path.exists(json_path):
            print(f"ROI: No json found for {filename}")
            return FileResponse(file_path)
            
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        bbox = data.get("bbox")
        if not bbox:
            print(f"ROI: No bbox in json for {filename}")
            return FileResponse(file_path)

        print(f"ROI: Drawing box for {filename}: {bbox}")
            
        img = cv2.imread(file_path)
        if img is None:
            return FileResponse(file_path)
            
        # Draw bounding box (bbox coordinates are normalized 0.0 - 1.0)
        h, w, _ = img.shape
        start_x = int(bbox["x"] * w)
        start_y = int(bbox["y"] * h)
        box_w = int(bbox["w"] * w)
        box_h = int(bbox["h"] * h)
        
        # Draw a neon blue/cyan box with 4px thickness
        cv2.rectangle(img, (start_x, start_y), (start_x + box_w, start_y + box_h), (255, 240, 0), 4)
        
        # Also draw the label text above the box
        label_text = data.get("label", "Object")
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(label_text, font, font_scale, thickness)[0]
        text_x = start_x
        text_y = max(start_y - 10, 0)
        
        # Draw text background
        cv2.rectangle(img, (text_x, text_y - text_size[1]), (text_x + text_size[0], text_y + 5), (255, 240, 0), -1)
        # Draw text foreground (dark)
        cv2.putText(img, label_text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness)

        # Encode image to memory buffer
        success, encoded_img = cv2.imencode('.jpg', img)
        if not success:
            return FileResponse(file_path)
            
        return Response(content=encoded_img.tobytes(), media_type="image/jpeg")

    except Exception as e:
        print(f"Error drawing ROI for {filename}: {e}")
        return FileResponse(file_path)

@router.post("/augment/{label}")
def trigger_manual_augmentation(label: str, background_tasks: BackgroundTasks):
    """
    Manually triggers LLM augmentation using one of the stored images for the label.
    """
    from backend.storage.collector import COLLECTOR_DIR
    
    label = label.strip().lower()
    if not os.path.exists(COLLECTOR_DIR):
        raise HTTPException(status_code=404, detail="No images found for label")
        
    pattern = os.path.join(COLLECTOR_DIR, f"{label}_*.jpg")
    files = glob.glob(pattern)
    
    if not files:
        raise HTTPException(status_code=404, detail="No images found for label")
        
    # Use the first available image as representative
    representative_image_path = files[0]
    img = cv2.imread(representative_image_path)
    
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to read representative image")
        
    # Trigger background task with a larger fetch parameter
    background_tasks.add_task(_run_llm_augmentation_bg, label, img, 50)
    
    return {"status": "started", "message": f"LLM augmentation started for '{label}'"}
