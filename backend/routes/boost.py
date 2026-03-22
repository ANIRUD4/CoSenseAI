"""
backend/routes/boost.py

Endpoints for the companion-app "Boost Accuracy" / "Deep Learn" feature.

POST /boost/start
  - Accepts { label, max_images }
  - Spawns a background job to download a public dataset, embed images,
    and append to the prototype store.
  - Returns { job_id } immediately so the app can poll for progress.

GET /boost/status/{job_id}
  - Returns current job progress: { status, progress, total, added, message }

GET /boost/jobs
  - Returns all recent jobs (for debugging).
"""

import glob
import os
import traceback

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.boost.dataset_resolver import resolve_dataset
from backend.boost.image_downloader import download_images_for_class
from backend.boost.job_store import create_job, get_job, list_jobs, update_job
from backend.storage.prototype_store import add_prototype, load_prototypes, recompute_all_means
from backend.utils.diversity import MIN_DIVERSITY, select_diverse_prototypes

router = APIRouter(prefix="/boost", tags=["Boost"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class BoostRequest(BaseModel):
    label: str
    max_images: int = 150


# ── Background task ───────────────────────────────────────────────────────────

def _run_boost_job(job_id: str, label: str, img: np.ndarray, max_images: int):
    """
    Full pipeline:
      1. Resolve label → dataset + class_name via Gemini
      2. Download max_images images from Open Images / COCO / web
      3. Embed each image via CLIP
      4. Diversity-gate and append to prototype store
      5. Recompute mean vector for the label
    """
    from perception.interface import get_embedding_from_image

    try:
        # ── Step 1: Dataset resolution ─────────────────────────────────────
        update_job(job_id, status="running", message="Consulting LLM to identify dataset...")
        resolution = resolve_dataset(label, img)
        canonical  = resolution["canonical_label"]
        dataset    = resolution["dataset"]
        class_name = resolution["class_name"]
        update_job(job_id, message=f"Identified: '{canonical}' in {dataset}/{class_name}. Downloading...")

        # ── Step 2: Download images ────────────────────────────────────────
        images = download_images_for_class(
            dataset=dataset,
            class_name=class_name,
            canonical_label=canonical,
            max_images=max_images,
        )
        if not images:
            update_job(job_id, status="failed", message="No images could be downloaded.")
            return

        total = len(images)
        update_job(job_id, total=total, message=f"Downloaded {total} images. Embedding...")

        # ── Step 3: Load existing prototypes for diversity gating ──────────
        existing_protos  = load_prototypes().get(label, {}).get("prototypes", [])
        existing_vectors = [p["vector"] for p in existing_protos]

        # ── Step 4: Embed + diversity gate + store ─────────────────────────
        candidates = []
        for i, image in enumerate(images):
            try:
                emb = get_embedding_from_image(image)
                if emb is not None:
                    candidates.append(emb)
            except Exception as e:
                print(f"BOOST: Embedding failed for image {i}: {e}")
            update_job(job_id, progress=i + 1)

        accepted, skipped = select_diverse_prototypes(
            candidates=candidates,
            existing_vectors=existing_vectors,
            min_diversity=MIN_DIVERSITY,
        )

        added = 0
        for emb in accepted:
            if add_prototype(label, emb, source="boosted"):
                added += 1

        print(
            f"BOOST: job={job_id} label='{label}' "
            f"downloaded={total} embedded={len(candidates)} "
            f"accepted={len(accepted)} skipped={skipped} stored={added}"
        )

        # ── Step 5: Refresh mean vector ────────────────────────────────────
        recompute_all_means()

        update_job(
            job_id,
            status="done",
            added=added,
            message=(
                f"Done! {added} new diverse embeddings added from {total} downloaded images. "
                f"Recognition accuracy for '{label}' is now boosted."
            ),
        )

    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", message=f"Error: {str(e)}")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start")
def start_boost(req: BoostRequest, background_tasks: BackgroundTasks):
    """
    Start a boost job for the given label.
    Finds a representative image from the collector directory.
    Returns a job_id immediately for polling.
    """
    label = req.label.strip().lower()
    if not label:
        raise HTTPException(status_code=400, detail="label is required")

    from backend.storage.collector import COLLECTOR_DIR
    pattern  = os.path.join(COLLECTOR_DIR, f"{label}_*.jpg")
    files    = glob.glob(pattern)

    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"No collected images found for label '{label}'. Teach it on the Pi first.",
        )

    img = cv2.imread(files[0])
    if img is None:
        raise HTTPException(status_code=500, detail="Could not read the representative image.")

    job_id = create_job(label)
    update_job(job_id, total=req.max_images)

    background_tasks.add_task(_run_boost_job, job_id, label, img, req.max_images)

    return {
        "status":  "started",
        "job_id":  job_id,
        "label":   label,
        "message": f"Boost pipeline started for '{label}' — poll /boost/status/{job_id}",
    }


@router.get("/status/{job_id}")
def get_boost_status(job_id: str):
    """
    Returns current status of a boost job.
    The companion app polls this every 2 seconds to update its progress bar.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs")
def list_boost_jobs():
    """Return all recent boost jobs (useful for debugging from the companion app)."""
    return {"jobs": list_jobs()}
