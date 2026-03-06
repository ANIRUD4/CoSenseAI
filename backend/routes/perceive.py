from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2
from backend.adapters import get_embedding

router = APIRouter(prefix="/perceive", tags=["Perception"])


@router.post("/embedding")
def perceive_embedding(file: UploadFile = File(...)):
    try:
        # 1. Read raw bytes
        image_bytes = file.file.read()

        if not image_bytes:
            raise ValueError("Empty image received")

        # 2. Convert bytes → NumPy array
        np_arr = np.frombuffer(image_bytes, np.uint8)

        # 3. Decode image (BGR format)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image file")

        # 4. Get embedding via focus-based ROI
        emb_result = get_embedding(image, use_focus_roi=True)

        return {
            "embedding": emb_result["embedding"],
            "roi_mode": emb_result.get("roi_mode"),
            "focus_hint": emb_result.get("focus_hint"),
        }


    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
