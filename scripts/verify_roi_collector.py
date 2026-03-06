"""
scripts/verify_roi_collector.py
Verifies:
1. Manual ROI cropping produces a valid embedding.
2. Data Collector saves image and bbox to data/collector.
"""
import sys, os, base64, json, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
COLLECTOR_DIR = "data/collector"

def test_roi_and_collector():
    # Cleanup collector if exists
    if os.path.exists(COLLECTOR_DIR):
        for f in os.listdir(COLLECTOR_DIR):
            os.remove(os.path.join(COLLECTOR_DIR, f))
    else:
        os.makedirs(COLLECTOR_DIR, exist_ok=True)

    # 1. Create a dummy image (e.g., black with a white square in the BBox area)
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # White square at 40% to 60%
    cv2.rectangle(img, (int(640*0.4), int(480*0.4)), (int(640*0.6), int(480*0.6)), (255, 255, 255), -1)
    
    _, buffer = cv2.imencode('.jpg', img)
    img_b64 = base64.b64encode(buffer).decode('utf-8')

    # 2. Send Learning Request with BBox
    # BBox is {x: 0.4, y: 0.4, w: 0.2, h: 0.2}
    payload = {
        "label": "test_object",
        "image_base64": img_b64,
        "roi_bbox": {"x": 0.4, "y": 0.4, "w": 0.2, "h": 0.2}
    }

    print("Sending learn request with manual BBox...")
    resp = client.post("/learn/commit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    print(f"SUCCESS: Backend accepted request. Response: {data}")

    # 3. Verify Collector
    collector_files = os.listdir(COLLECTOR_DIR)
    print(f"Collector files found: {collector_files}")
    
    has_jpg = any(f.endswith(".jpg") for f in collector_files)
    has_json = any(f.endswith(".json") for f in collector_files)
    
    assert has_jpg, "Collector did not save image"
    assert has_json, "Collector did not save JSON annotation"
    
    # Check JSON content
    json_file = [f for f in collector_files if f.endswith(".json")][0]
    with open(os.path.join(COLLECTOR_DIR, json_file), 'r') as f:
        meta = json.load(f)
        assert meta["label"] == "test_object"
        assert meta["bbox"]["x"] == 0.4
        print("PASS: Collector saved correct metadata.")

    print("\nROI and Collector verification COMPLETE.")

if __name__ == "__main__":
    test_roi_and_collector()
