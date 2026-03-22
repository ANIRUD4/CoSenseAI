"""
backend/boost/image_downloader.py

Downloads images for a given object class from:
  1. Open Images v7 — using the public CSV manifest (no API key needed).
     First run downloads ~1 GB CSV and caches it to data/openimages_index.csv.
  2. COCO 2017 — using the public annotations JSON.
  3. Web fallback — DuckDuckGo then Wikipedia (mirrors the existing llm_augment.py logic).

Each function returns a List[np.ndarray] of decoded BGR images.
"""

import os
import io
import csv
import json
import random
import httpx
import cv2
import numpy as np
from PIL import Image
from typing import List
from duckduckgo_search import DDGS

# ── Constants ─────────────────────────────────────────────────────────────────

CACHE_DIR = "data/boost_cache"
OI_INDEX_PATH = os.path.join(CACHE_DIR, "openimages_index.csv")
COCO_ANN_PATH = os.path.join(CACHE_DIR, "coco_instances_val2017.json")

# Open Images v7 public image-level label CSV (train split, ~9M rows)
# We use the smaller "validation" CSV which is ~600k rows and ~50 MB.
OI_VALIDATION_CSV_URL = (
    "https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions.csv"
)
OI_VALIDATION_LABELS_URL = (
    "https://storage.googleapis.com/openimages/v7/oidv7-validation-annotations-human-imagelabels.csv"
)
OI_VALIDATION_IMAGES_URL = (
    "https://storage.googleapis.com/openimages/v7/oidv7-validation-images-with-rotation.csv"
)
COCO_ANN_URL = (
    "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

_WIKI_HEADERS = {
    "User-Agent": "IntelShareAI/1.0 (https://github.com/IntelShareAI; user@example.com) IntelShareAI-Core/1.0",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _download_file(url: str, dest: str, desc: str = ""):
    """Download a file from URL to dest path if not already cached."""
    if os.path.exists(dest):
        print(f"BOOST: Cache hit for {desc or dest}")
        return
    print(f"BOOST: Downloading {desc or url} → {dest}")
    with httpx.Client(timeout=120, follow_redirects=True, http2=True) as client:
        resp = client.get(url, headers=_HEADERS)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
    print(f"BOOST: Downloaded {desc}")


def _decode_image(content: bytes) -> np.ndarray | None:
    """Decode raw image bytes to OpenCV BGR image."""
    try:
        pil_img = Image.open(io.BytesIO(content)).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def _download_image_urls(urls: List[str], max_images: int) -> List[np.ndarray]:
    """Download a list of image URLs, return decoded np.ndarray images."""
    images = []
    random.shuffle(urls)
    with httpx.Client(timeout=10, follow_redirects=True, http2=True) as client:
        for url in urls:
            if len(images) >= max_images:
                break
            try:
                resp = client.get(url, headers=_HEADERS)
                img = _decode_image(resp.content)
                if img is not None:
                    images.append(img)
            except Exception as e:
                print(f"BOOST: Failed to download {url}: {e}")
                continue
    return images


# ── Open Images Downloader ────────────────────────────────────────────────────

def _load_oi_image_urls(class_mid: str, max_images: int) -> List[str]:
    """
    Returns a list of image URLs for the given Open Images MID class.
    Uses the validation split (~41k images) for speed and reasonable size.
    Falls back to an empty list if CSVs can't be fetched.
    """
    _ensure_cache_dir()

    labels_path = os.path.join(CACHE_DIR, "oi_val_labels.csv")
    images_path = os.path.join(CACHE_DIR, "oi_val_images.csv")

    try:
        _download_file(OI_VALIDATION_LABELS_URL, labels_path, "OI validation labels CSV")
        _download_file(OI_VALIDATION_IMAGES_URL, images_path, "OI validation images CSV")
    except Exception as e:
        print(f"BOOST: Could not download Open Images CSVs: {e}")
        return []

    # Build image_id → URL map
    print("BOOST: Building Open Images URL index...")
    id_to_url = {}
    try:
        with open(images_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                image_id = row.get("ImageID", "")
                original_url = row.get("OriginalURL", "")
                if image_id and original_url:
                    id_to_url[image_id] = original_url
    except Exception as e:
        print(f"BOOST: Failed to parse images CSV: {e}")
        return []

    # Collect image IDs that match the class MID
    matching_ids = []
    try:
        with open(labels_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("LabelName") == class_mid and row.get("Confidence", "0") == "1":
                    matching_ids.append(row["ImageID"])
    except Exception as e:
        print(f"BOOST: Failed to parse labels CSV: {e}")
        return []

    print(f"BOOST: Found {len(matching_ids)} Open Images candidates for {class_mid}")

    # Sample and resolve URLs
    sampled = random.sample(matching_ids, min(len(matching_ids), max_images * 2))
    urls = [id_to_url[img_id] for img_id in sampled if img_id in id_to_url]
    return urls[:max_images * 2]  # Oversample to account for download failures


def download_openimages_class(class_mid: str, max_images: int = 150) -> List[np.ndarray]:
    """
    Download and decode up to `max_images` images for an Open Images MID class.
    """
    print(f"BOOST: Starting Open Images download for class='{class_mid}', max={max_images}")
    urls = _load_oi_image_urls(class_mid, max_images)
    if not urls:
        print(f"BOOST: No URLs found for Open Images class '{class_mid}'")
        return []
    images = _download_image_urls(urls, max_images)
    print(f"BOOST: Downloaded {len(images)} images from Open Images for '{class_mid}'")
    return images


# ── COCO Downloader ───────────────────────────────────────────────────────────

def download_coco_class(class_name: str, max_images: int = 150) -> List[np.ndarray]:
    """
    Download and decode images for a COCO class name using the val2017 split.
    Downloads the COCO val2017 annotations JSON (~25MB) if not cached.
    """
    _ensure_cache_dir()
    ann_path = os.path.join(CACHE_DIR, "coco_val2017_annotations.json")

    try:
        _download_file(
            "https://storage.googleapis.com/tpu-pytorch/datasets/coco/annotations/instances_val2017.json",
            ann_path,
            "COCO val2017 annotations"
        )
    except Exception as e:
        print(f"BOOST: Could not download COCO annotations: {e}")
        return []

    try:
        with open(ann_path, "r") as f:
            coco = json.load(f)
    except Exception as e:
        print(f"BOOST: Could not parse COCO annotations: {e}")
        return []

    # Find category ID
    cat_id = None
    for cat in coco.get("categories", []):
        if cat["name"].lower() == class_name.lower():
            cat_id = cat["id"]
            break

    if cat_id is None:
        print(f"BOOST: COCO class '{class_name}' not found.")
        return []

    # Collect image IDs for this category
    image_ids = set()
    for ann in coco.get("annotations", []):
        if ann["category_id"] == cat_id:
            image_ids.add(ann["image_id"])

    # Build COCO image URLs (val2017 is public)
    id_to_info = {img["id"]: img for img in coco.get("images", [])}
    urls = []
    for img_id in list(image_ids):
        info = id_to_info.get(img_id)
        if info:
            coco_url = info.get("coco_url") or info.get("flickr_url")
            if coco_url:
                urls.append(coco_url)

    print(f"BOOST: Found {len(urls)} COCO images for class='{class_name}'")
    if not urls:
        return []

    images = _download_image_urls(urls, max_images)
    print(f"BOOST: Downloaded {len(images)} images from COCO for '{class_name}'")
    return images


# ── Web / DuckDuckGo Fallback ─────────────────────────────────────────────────

def _fetch_images_from_serper(query: str, max_images: int = 50) -> List[np.ndarray]:
    """Helper to fetch images using Serper.dev API."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []

    print(f"BOOST: Fetching images from Serper.dev for '{query}'...")
    url = "https://google.serper.dev/images"
    payload = json.dumps({"q": query, "num": max_images})
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    images = []
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, headers=headers, content=payload)
            if response.status_code == 200:
                results = response.json().get("images", [])
                for item in results:
                    img_url = item.get("imageUrl")
                    if img_url:
                        try:
                            # Use standard browser headers for external image hosts
                            img_resp = client.get(img_url, headers=_HEADERS, timeout=10)
                            if img_resp.status_code == 200:
                                img = _decode_image(img_resp.content)
                                if img is not None:
                                    images.append(img)
                        except Exception:
                            continue
                    if len(images) >= max_images:
                        break
    except Exception as e:
        print(f"BOOST: Serper.dev fetch failed: {e}")
    
    return images


def download_web_images(query: str, max_images: int = 50) -> List[np.ndarray]:
    """
    Fallback: fetch images from Serper.dev (preferred), then DuckDuckGo, then Wikipedia.
    """
    images = []
    
    # ── 1. Serper.dev (Premium Choice) ──
    images = _fetch_images_from_serper(query, max_images)
    if len(images) >= 5:
        print(f"BOOST: Serper.dev returned {len(images)} images.")
        return images

    # ── 2. DuckDuckGo ──
    try:
        # We use a context manager for DDGS as recommended in latest docs
        with DDGS(headers=_HEADERS) as ddgs:
            results = ddgs.images(
                keywords=query,
                region="us-en",
                safesearch="off",
                max_results=max_images,
            )
            with httpx.Client(timeout=10, follow_redirects=True, http2=True) as client:
                for result in results:
                    if len(images) >= max_images:
                        break
                    img_url = result.get("image")
                    if not img_url:
                        continue
                    try:
                        # Standard browser headers help avoid 403 on image hosts
                        resp = client.get(img_url, headers=_HEADERS)
                        if resp.status_code == 200:
                            img = _decode_image(resp.content)
                            if img is not None:
                                images.append(img)
                    except Exception:
                        continue
    except Exception as e:
        print(f"BOOST: DDG fallback failed: {e}")

    # ── 2. Wikipedia Fallback ──
    if len(images) < 5:  # If DDG failed or returned very few results
        print(f"BOOST: Insufficient results for '{query}', trying Wikipedia...")
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query", "format": "json", "prop": "pageimages",
                "generator": "search", "gsrsearch": query,
                "gsrlimit": max_images, "pithumbsize": 800,
            }
            wiki_headers = {
                "User-Agent": "IntelShareAI/1.0 (contact: user@example.com)",
            }
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                print(f"BOOST: Querying Wikipedia API: {url}")
                wiki_api_headers = _WIKI_HEADERS.copy()
                wiki_api_headers["Referer"] = "https://en.wikipedia.org/"
                resp = client.get(url, params=params, headers=wiki_api_headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        pages = data.get("query", {}).get("pages", {})
                        for pid, page in pages.items():
                            if len(images) >= max_images:
                                break
                            th = page.get("thumbnail", {}).get("source")
                            if th:
                                try:
                                    # Wikipedia images require identifying User-Agents and Referer
                                    wiki_img_headers = _WIKI_HEADERS.copy()
                                    wiki_img_headers["Referer"] = "https://en.wikipedia.org/"
                                    r = client.get(th, headers=wiki_img_headers)
                                    if r.status_code == 200:
                                        img = _decode_image(r.content)
                                        if img is not None:
                                            images.append(img)
                                    else:
                                        print(f"BOOST: Wikipedia image download failed: {r.status_code} for {th}")
                                except Exception as e:
                                    print(f"BOOST: Wikipedia image error: {e}")
                                    continue
                    except Exception as e:
                        print(f"BOOST: Wikipedia JSON parse error: {e}")
                else:
                    print(f"BOOST: Wikipedia API returned {resp.status_code}")
        except Exception as e:
            print(f"BOOST: Wikipedia fallback failed: {e}")

    print(f"BOOST: Web fallback got {len(images)} images for '{query}'")
    return images


# ── Main Dispatcher ───────────────────────────────────────────────────────────

def download_images_for_class(
    dataset: str,
    class_name: str,
    canonical_label: str,
    max_images: int = 150,
) -> List[np.ndarray]:
    """
    Route to the correct downloader based on the dataset choice.
    Falls back automatically if the primary source returns nothing.
    """
    if dataset == "openimages":
        images = download_openimages_class(class_name, max_images)
    elif dataset == "coco":
        images = download_coco_class(class_name, max_images)
    else:
        images = []

    if not images:
        print(f"BOOST: Primary source empty, falling back to web for '{canonical_label}'")
        images = download_web_images(canonical_label, min(max_images, 50))

    return images
