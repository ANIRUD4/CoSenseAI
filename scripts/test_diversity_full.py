"""
scripts/test_diversity_full.py
Verifies that teaching an object still works even if the label already has 15 prototypes.
"""
import sys, os, json, base64, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.storage.prototype_store import STORE_PATH

client = TestClient(app)

def test_full_label_learning():
    # 1. Reset store
    if os.path.exists(STORE_PATH):
        os.remove(STORE_PATH)
    
    label = "full_object"
    
    # 2. Fill up 15 prototypes
    print(f"Filling up 15 prototypes for '{label}'...")
    for i in range(15):
        # Create unique image for each - use random colors and positions to force CLIP diversity
        img = np.random.randint(0, 50, (300, 300, 3), dtype=np.uint8)
        cv2.circle(img, (int(np.random.rand()*300), int(np.random.rand()*300)), 50, (255, 255, 255), -1)
        cv2.putText(img, f"IMG_{i}_{time.time()}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buffer = cv2.imencode('.jpg', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        
        resp = client.post("/learn/commit", json={
            "label": label,
            "image_base64": img_b64
        })
        if resp.status_code != 200:
            print(f"FAILED at index {i}: {resp.json()}")
            return
        
        print(f"Added prototype {i+1}...")
    
    # Verify we are at 15
    with open(STORE_PATH, 'r') as f:
        data = json.load(f)
        count = len(data[label]["prototypes"])
        print(f"Current prototype count: {count}")
        assert count == 15

    # 3. Try to add one more (the 16th)
    print("Attempting to add 16th prototype (should trigger eviction)...")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.putText(img, "16", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', img)
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    
    resp = client.post("/learn/commit", json={
        "label": label,
        "image_base64": img_b64
    })
    
    if resp.status_code == 200:
        print("SUCCESS: 16th prototype accepted via eviction.")
        with open(STORE_PATH, 'r') as f:
            data = json.load(f)
            assert len(data[label]["prototypes"]) == 15
        print("PASS: Verified store remains at cap (15) after eviction.")
    else:
        print(f"FAIL: 16th prototype rejected with {resp.status_code}: {resp.json()}")

if __name__ == "__main__":
    test_full_label_learning()
