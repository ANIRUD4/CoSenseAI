"""
scripts/reproduce_learn_400.py
Mimics a frontend request to /learn/commit and prints the exact error detail.
"""
import sys, os, base64, json
import numpy as np
import cv2
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

client = TestClient(app)

def reproduce():
    label = "full_object"
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "TEST", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img)
    # Include the data URL prefix as the browser does
    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

    payload = {
        "label": "repro_object",
        "image_base64": img_b64,
        "action": "test_action",
        "roi_bbox": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
    }

    print("Sending request...")
    resp = client.post("/learn/commit", json=payload)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error Detail: {resp.json().get('detail')}")
    else:
        print(f"Success! Response: {resp.json()}")

if __name__ == "__main__":
    reproduce()
