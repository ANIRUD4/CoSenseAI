"""
backend/llm_augment.py

LLM-based dataset augmentation service for IntelShare AI.

Flow:
  1. The user captures 3-7 images of an object in Learn mode.
  2. Each image is saved (via collector.py) and encoded as base64.
  3. This service sends one representative image + label to an LLM (Google Gemini Vision)
     to identify the object and fetch relevant search keywords.
  4. It then fetches a batch of real similar images from DuckDuckGo (no API key needed).
  5. All fetched images are passed through the CLIP embedding engine.
  6. The resulting embeddings are returned to be appended to the prototype store.

The user only sees the result (improved accuracy); all of this happens transparently.
"""

import base64
import io
import os
import httpx
import cv2
import numpy as np
from typing import List
from PIL import Image
from duckduckgo_search import DDGS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_image_for_llm(image: np.ndarray) -> str:
    """Encode an OpenCV BGR image to JPEG base64 string."""
    success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("Failed to encode image to JPEG")
    return base64.b64encode(buffer).decode("utf-8")


def _fetch_images_from_wikipedia(query: str, max_images: int = 10) -> List[np.ndarray]:
    """
    Fallback: Fetches images from Wikipedia API if DuckDuckGo rate limits.
    """
    images = []
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": max_images,
        "pithumbsize": 800,
    }
    headers = {
        "User-Agent": "IntelShareAI/1.0 (https://github.com/)"
    }
    
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_info in pages.items():
                if "thumbnail" in page_info:
                    img_url = page_info["thumbnail"]["source"]
                    try:
                        img_resp = client.get(img_url, headers=headers)
                        pil_img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        images.append(cv_img)
                        if len(images) >= max_images:
                            break
                    except Exception as e:
                        print(f"LLM_AUGMENT: Wikipedia image download error: {e}")
                        continue
    except Exception as e:
        print(f"LLM_AUGMENT: Wikipedia API error: {e}")
        
    print(f"LLM_AUGMENT: Fetched {len(images)} images from Wikipedia for '{query}'")
    return images


def _fetch_images_from_web(query: str, max_images: int = 10) -> List[np.ndarray]:
    """
    Fetches real images from the web using DuckDuckGo, with a fallback to Wikipedia.
    """
    images = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        results = DDGS().images(
            keywords=query,
            region="us-en",
            safesearch="off",
            max_results=max_images,
        )
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            for result in results:
                img_url = result.get("image")
                if not img_url:
                    continue
                try:
                    resp = client.get(img_url, headers=headers)
                    pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    images.append(cv_img)
                except Exception as e:
                    print(f"LLM_AUGMENT: Failed to download image from {img_url}: {e}")
                    continue
    except Exception as e:
        print(f"LLM_AUGMENT: DDG Web image fetch error: {e}")
        
    # Fallback to Wikipedia if DuckDuckGo failed or returned 0 results due to Rate Limit
    if not images:
        print(f"LLM_AUGMENT: DuckDuckGo failed/returned 0 images. Falling back to Wikipedia...")
        images = _fetch_images_from_wikipedia(query, max_images)

    print(f"LLM_AUGMENT: Total fetched {len(images)} real images for query='{query}'")
    return images


def _ask_llm_for_keywords(label: str, image_b64: str) -> str:
    """
    Sends the label + a representative image to Google Gemini Vision to get
    a precise search query for fetching similar real-world images.

    Falls back to using the label itself if GEMINI_API_KEY is not set or fails.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("LLM_AUGMENT: GEMINI_API_KEY not set — using label as search query.")
        return label

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                    {
                        "text": (
                            f"The user wants to teach an AI to recognise: '{label}'. "
                            "Look at the image and describe the most accurate web image search "
                            "query (5 words max) that would find similar real photos of this "
                            "exact object. Reply with ONLY the search query, nothing else."
                        )
                    },
                ]
            }
        ]
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                with open("llm_debug.txt", "a") as f:
                    f.write(f"LLM_AUGMENT: Gemini API failed with {resp.status_code}. Response: {resp.text}\n")
                print(f"LLM_AUGMENT: Gemini API failed with {resp.status_code}. Response: {resp.text}")
            resp.raise_for_status()
            query = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", label)
                .strip()
            )
            print(f"LLM_AUGMENT: Gemini suggested query='{query}' for label='{label}'")
            return query or label
    except Exception as e:
        print(f"LLM_AUGMENT: Gemini API exception: {e} — falling back to label.")
        return label


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def augment_with_web_images(
    label: str,
    representative_image: np.ndarray,
    max_web_images: int = 10,
) -> List[List[float]]:
    """
    Main entry point called from the /learn/commit route (background task).

    1. Asks Gemini to generate a search query from label + image.
    2. Fetches real similar images from the web.
    3. Converts each to an embedding using the existing CLIP engine.
    4. Returns a list of embeddings (float lists) ready to be appended
       to the prototype store.

    Args:
        label:               User-assigned label string.
        representative_image: One of the user-captured images (OpenCV BGR).
        max_web_images:      How many web images to attempt to download.

    Returns:
        List of embedding vectors (each is a List[float]).
    """
    from perception.interface import get_embedding_from_image  # local import to avoid circular

    # 1. Ask LLM for keywords
    img_b64 = _encode_image_for_llm(representative_image)
    search_query = _ask_llm_for_keywords(label, img_b64)

    # 2. Fetch real images
    web_images = _fetch_images_from_web(search_query, max_images=max_web_images)
    if not web_images:
        print(f"LLM_AUGMENT: No web images fetched for '{label}', skipping augmentation.")
        return []

    # 3. Embed each image
    embeddings = []
    for img in web_images:
        try:
            emb = get_embedding_from_image(img)
            if emb is not None:
                embeddings.append(emb)
        except Exception as e:
            print(f"LLM_AUGMENT: Embedding failed for one image: {e}")

    print(
        f"LLM_AUGMENT: Generated {len(embeddings)} web embeddings "
        f"for label='{label}' (from {len(web_images)} fetched images)"
    )
    return embeddings
