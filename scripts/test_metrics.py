"""
scripts/test_metrics.py

Verifies the performance metrics system:
1. Event logging in metrics_store.
2. API summary endpoint.
3. Graph generation.

Run from project root:
    python -m scripts.test_metrics
"""

import sys, os, time, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. SETUP TEMP METRICS PATH BEFORE IMPORTS
tmp_dir = tempfile.mkdtemp()
test_metrics_path = os.path.join(tmp_dir, "test_metrics.json")

import backend.storage.metrics_store as ms
ms.METRICS_PATH = test_metrics_path

from fastapi.testclient import TestClient
from backend.main import app
import backend.utils.visualization as viz

client = TestClient(app)

def test_metrics_flow():
    try:
        # A) Log some events via store directly
        ms.log_event("apple", True, 0.9)
        ms.log_event("apple", True, 0.85)
        ms.log_event("orange", False, 0.7) # Correction
        
        # B) Check store
        data = ms.load_metrics()
        assert data["total_confirmed"] == 2
        assert data["total_corrected"] == 1
        assert len(data["events"]) == 3
        print("PASS: Store logging confirmed correctly.")
        
        # C) Check API Summary
        resp = client.get("/metrics/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["total_feedbacks"] == 3
        assert summary["global_accuracy"] == round(2/3, 4)
        print(f"PASS: API Summary correct. Accuracy: {summary['global_accuracy']}")
        
        # D) Check Graph Generation
        resp = client.get("/metrics/graph/accuracy")
        assert resp.status_code == 200
        graph_data = resp.json()
        assert graph_data["encoding"] == "base64"
        assert len(graph_data["data"]) > 100 # Should have some image data
        print("PASS: Accuracy graph generated as Base64.")
        
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    print("=== Performance Metrics System Tests ===")
    test_metrics_flow()
    print("\nAll metrics system tests passed.")

