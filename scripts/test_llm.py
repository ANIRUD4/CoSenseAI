import os
import base64
import requests
import time

API_URL = "http://127.0.0.1:8000"
IMAGE_PATH = os.path.join("data", "collector", "rubiks cube_1773077251397.jpg")

def test_llm_augmentation():
    if not os.path.exists(IMAGE_PATH):
        print(f"Test image not found at {IMAGE_PATH}")
        return

    print(f"Loading image {IMAGE_PATH}")
    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "label": "rubiks cube",
        "image_base64": image_b64
    }

    print("Sending request to /learn/commit...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/learn/commit",
            json=payload,
            timeout=30 # LLM might take a few seconds
        )
        end_time = time.time()
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Time: {end_time - start_time:.2f} seconds")
        print(f"Response Body: {response.json()}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_llm_augmentation()
