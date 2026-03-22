"""
backend/boost/dataset_resolver.py

Uses Google Gemini Vision to interpret a label + representative image and
return a structured dataset resolution:
  - canonical_label: human-readable refined object name
  - dataset: "openimages" | "coco" | "web"
  - class_name: Open Images MID (e.g. "/m/07j87") or COCO class name (e.g. "bottle")

Falls back to raw label with dataset="web" if Gemini is unavailable or fails.
"""

import os
import json
import base64
import httpx
import cv2
import numpy as np


def _encode_image(image: np.ndarray) -> str:
    """Encode a BGR OpenCV image to base64 JPEG string."""
    success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("Failed to encode image to JPEG")
    return base64.b64encode(buffer).decode("utf-8")


# A subset of common Open Images MIDs for well-known objects.
# This avoids a full API call for everyday objects.
_OPENIMAGES_COMMON = {
    "bottle":       "/m/04dr76w",
    "water bottle": "/m/07j87",
    "cup":          "/m/02jvh9",
    "mug":          "/m/083wq",
    "phone":        "/m/050k8",
    "mobile phone": "/m/050k8",
    "book":         "/m/0bt_c3",
    "chair":        "/m/01mzpv",
    "laptop":       "/m/01c648",
    "keyboard":     "/m/01m2v",
    "mouse":        "/m/0d4v4",
    "pen":          "/m/0dv9c",
    "pencil":       "/m/0jyfg",
    "apple":        "/m/014j1m",
    "banana":       "/m/09qck",
    "orange":       "/m/0cyhj_",
    "spoon":        "/m/0cmx8",
    "fork":         "/m/04ctx",
    "knife":        "/m/04v6l4",
    "glasses":      "/m/0jyfg",
    "bag":          "/m/0584n8",
    "backpack":     "/m/01940j",
    "shoe":         "/m/01rkbr",
    "hat":          "/m/02dl1y",
    "clock":        "/m/01x3z",
    "remote":       "/m/0qjjc",
    "scissors":     "/m/01lsmm",
    "toothbrush":   "/m/012xff",
    "comb":         "/m/09csl",
    "umbrella":     "/m/0hnnb",
    "key":          "/m/0c_jw",
    "wallet":       "/m/0b3fp9",
    "headphones":   "/m/0283dt1",
    "watch":        "/m/06zmk",
    "rubiks cube":  "/m/06lxs",
    "rubiikscube":  "/m/06lxs",
}

# COCO class names (80 classes subset for fallback)
_COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana",
    "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table",
    "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock",
    "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
]


def resolve_dataset(label: str, image: np.ndarray) -> dict:
    """
    Resolve a label + image into a canonical label and dataset class.

    Returns a dict like:
      {
        "canonical_label": "plastic water bottle",
        "dataset": "openimages",
        "class_name": "/m/07j87"
      }

    Falls back progressively:
      1. Gemini Vision JSON response
      2. Common Open Images lookup table
      3. COCO fuzzy match
      4. Web (DuckDuckGo) fallback
    """
    label_lower = label.strip().lower()

    # ── 1. Try Gemini Vision ──────────────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            img_b64 = _encode_image(image)
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={api_key}"
            )
            prompt = (
                f"The user is teaching an AI system to recognise: '{label}'. "
                "Look at the image and respond with ONLY a valid JSON object "
                "(no markdown, no explanation) with these exact keys:\n"
                "  canonical_label: a short, precise English name for the object\n"
                "  dataset: one of 'openimages' or 'coco' (whichever has more images of this type)\n"
                "  class_name: if 'openimages', the Open Images MID code (e.g. /m/07j87); "
                "if 'coco', the exact COCO class string (e.g. bottle)\n"
                "Example: {\"canonical_label\": \"plastic water bottle\", "
                "\"dataset\": \"openimages\", \"class_name\": \"/m/07j87\"}"
            )
            payload = {
                "contents": [{
                    "parts": [
                        {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
                        {"text": prompt},
                    ]
                }]
            }
            with httpx.Client(timeout=20) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                text = (
                    resp.json()
                    .get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                # Strip markdown fences if Gemini wraps them
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                result = json.loads(text)
                canonical = result.get("canonical_label", label)
                dataset   = result.get("dataset", "web")
                class_nm  = result.get("class_name", label)
                print(f"BOOST: Gemini resolved '{label}' → '{canonical}' ({dataset}/{class_nm})")
                return {
                    "canonical_label": canonical,
                    "dataset": dataset,
                    "class_name": class_nm,
                }
        except Exception as e:
            print(f"BOOST: Gemini resolution failed: {e} — using local lookup.")

    # ── 2. Local Open Images lookup ───────────────────────────────────────────
    if label_lower in _OPENIMAGES_COMMON:
        mid = _OPENIMAGES_COMMON[label_lower]
        print(f"BOOST: Local OI lookup '{label}' → {mid}")
        return {"canonical_label": label, "dataset": "openimages", "class_name": mid}

    # ── 3. COCO fuzzy match ───────────────────────────────────────────────────
    for coco_cls in _COCO_CLASSES:
        if label_lower in coco_cls or coco_cls in label_lower:
            print(f"BOOST: COCO match '{label}' → '{coco_cls}'")
            return {"canonical_label": coco_cls, "dataset": "coco", "class_name": coco_cls}

    # ── 4. Web fallback ───────────────────────────────────────────────────────
    print(f"BOOST: No dataset match for '{label}' — falling back to web search.")
    return {"canonical_label": label, "dataset": "web", "class_name": label}
