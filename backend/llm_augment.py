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
from perception.similarity import cosine_similarity

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
    # Wikipedia requires a descriptive User-Agent
    headers = {
        "User-Agent": "IntelShareAI/1.0 (contact: user@example.com)"
    }
    
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                print(f"LLM_AUGMENT: Wikipedia API returned {resp.status_code}")
                return []
                
            try:
                data = resp.json()
            except Exception:
                print("LLM_AUGMENT: Wikipedia API returned non-JSON response.")
                return []

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "thumbnail" in page_info:
                    img_url = page_info["thumbnail"]["source"]
                    try:
                        # Wikipedia images often require a Referer and a standard Browser-Agent
                        img_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": "https://en.wikipedia.org/",
                        }
                        img_resp = client.get(img_url, headers=img_headers)
                        if img_resp.status_code == 200:
                            pil_img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                            images.append(cv_img)
                            if len(images) >= max_images:
                                break
                        else:
                            print(f"LLM_AUGMENT: Wikipedia image download failed: {img_resp.status_code} for {img_url}")
                    except Exception as e:
                        print(f"LLM_AUGMENT: Wikipedia image download error: {e}")
                        continue
    except Exception as e:
        print(f"LLM_AUGMENT: Wikipedia API error: {e}")
        
    print(f"LLM_AUGMENT: Fetched {len(images)} images from Wikipedia for '{query}'")
    return images


def _fetch_images_from_serper(query: str, max_images: int = 10) -> List[np.ndarray]:
    """
    Fetches real images using the Serper.dev (Google Search) API.
    Requires SERPER_API_KEY in environment.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []

    url = "https://google.serper.dev/images"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": max_images
    }

    images = []
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"LLM_AUGMENT: Serper API failed with {resp.status_code}")
                return []
            
            results = resp.json().get("images", [])
            for result in results:
                img_url = result.get("imageUrl")
                if not img_url:
                    continue
                try:
                    img_resp = client.get(img_url, timeout=10)
                    if img_resp.status_code == 200:
                        pil_img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        images.append(cv_img)
                        if len(images) >= max_images:
                            break
                except Exception as e:
                    print(f"LLM_AUGMENT: Failed to download Serper image from {img_url}: {e}")
                    continue
    except Exception as e:
        print(f"LLM_AUGMENT: Serper API exception for '{query}': {e}")
    
    print(f"LLM_AUGMENT: Fetched {len(images)} images from Serper for '{query}'")
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
            "Chrome/120.0.0.0 Safari/537.36 IntelShareAI/1.0"
        )
    }

    # 1. Try Serper.dev API first (High Reliability)
    images = _fetch_images_from_serper(query, max_images)
    if len(images) >= 3:
        return images

    # 2. Try DuckDuckGo (Scraping - Fallback)
    try:
        with DDGS(headers=headers) as ddgs:
            results = ddgs.images(
                keywords=query,
                region="us-en",
                safesearch="off",
                max_results=max_images,
            )
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                for result in results:
                    img_url = result.get("image")
                    if not img_url:
                        continue
                    try:
                        resp = client.get(img_url, headers=headers)
                        if resp.status_code == 200:
                            pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                            images.append(cv_img)
                            if len(images) >= max_images:
                                break
                    except Exception as e:
                        print(f"LLM_AUGMENT: Failed to download image from {img_url}: {e}")
                        continue
    except Exception as e:
        print(f"LLM_AUGMENT: DDG Web image fetch error for '{query}': {e}")
        
    # Fallback to Wikipedia if DuckDuckGo failed or returned very few results
    if len(images) < 3:
        print(f"LLM_AUGMENT: DuckDuckGo returned insufficient images ({len(images)}). Falling back to Wikipedia...")
        images.extend(_fetch_images_from_wikipedia(query, max_images - len(images)))

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
                            f"The user has defined this object as: '{label}'.\n"
                            "1. Analyze the provided image.\n"
                            f"2. Generate an accurate web search query (max 6 words) that describes this specific object, keeping it strictly grounded in the concept of '{label}'.\n"
                            "3. Add visual keywords based on the photo (color, texture, specific type) that will help find similar real-world examples.\n"
                            "Reply with ONLY the search query, nothing else."
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

    # 3. Embed & Cleanse (Similarity Filter)
    embeddings = []
    
    # Get reference embedding for the user's photo to perform Cleanse
    try:
        ref_emb = get_embedding_from_image(representative_image)
    except Exception as e:
        print(f"LLM_AUGMENT: Failed to embed representative image: {e}")
        return []

    CLEANSE_THRESHOLD = 0.70 # Only keep web results that look similar to user's photo

    for img in web_images:
        try:
            emb = get_embedding_from_image(img)
            if emb is not None:
                # Similarity Cleanse logic
                sim = cosine_similarity(ref_emb, emb)
                if sim >= CLEANSE_THRESHOLD:
                    embeddings.append(emb)
                else:
                    print(f"LLM_AUGMENT: CLEANSE rejected image (sim={sim:.3f} < {CLEANSE_THRESHOLD})")
        except Exception as e:
            print(f"LLM_AUGMENT: Embedding failed for one image: {e}")

    print(
        f"LLM_AUGMENT: Generated {len(embeddings)} high-quality web embeddings "
        f"for label='{label}' (from {len(web_images)} fetched images, cleansed from potential noise)"
    )
    return embeddings
