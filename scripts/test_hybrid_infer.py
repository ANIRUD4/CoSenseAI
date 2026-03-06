"""
scripts/test_hybrid_infer.py

Verifies the high-level inference logic in backend/routes/infer.py.
Patches STORE_PATH BEFORE importing the app to ensure consistency.
Uses vectors that pass both the diversity gate (>0.25 dist) and 
the drift dedup (<0.95 sim).
"""

import sys, os, json, tempfile, shutil

# 1. SETUP TEMP STORE BEFORE ANY MODULE IMPORTS APP
tmp_dir = tempfile.mkdtemp()
test_store_path = os.path.join(tmp_dir, "test_prototypes.json")

import backend.storage.prototype_store as ps
ps.STORE_PATH = test_store_path

# 2. NOW IMPORT APP AND TEST CLIENT
from fastapi.testclient import TestClient
from backend.main import app
import numpy as np

client = TestClient(app)

def test_inference_logic():
    try:
        # 3. Setup Data
        # We need vectors with similarity between 0.0 and 0.75 to pass diversity gate
        # (Since 1 - 0.75 = 0.25 distance)
        
        # 'sparse' label: 2 orthogonal protos
        ps.add_prototype("sparse", [1.0] + [0.0]*511)
        ps.add_prototype("sparse", [0.0, 1.0] + [0.0]*510)
        
        # 'dense' label: 3 diverse protos (sim ~0.5 between each)
        # 1. [0, 0, 1, 0, ...]
        # 2. [0, 0, 0.707, 0.707, ...]  (sim to #1 = 0.707)
        # 3. [0, 0, 0.707, -0.707, ...] (sim to #1 = 0.707, sim to #2 = 0)
        v1 = [0.0, 0.0, 1.0] + [0.0]*509
        v2 = [0.0, 0.0, 0.707, 0.707] + [0.0]*508
        v3 = [0.0, 0.0, 0.707, -0.707] + [0.0]*508
        
        ps.add_prototype("dense", v1)
        ps.add_prototype("dense", v2)
        ps.add_prototype("dense", v3)
        
        data = ps.load_prototypes()
        dense_count = len(data.get("dense", {}).get("prototypes", []))
        sparse_count = len(data.get("sparse", {}).get("prototypes", []))
        
        print(f"DEBUG: Stored {dense_count} 'dense' and {sparse_count} 'sparse' protos.")
        
        # 4. Run Inference Requests
        
        # A) Match against 'dense'
        query_dense = [0.0, 0.0, 1.0] + [0.0]*509
        resp = client.post("/infer/", json={"embedding": query_dense})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        res = resp.json()
        
        if not res.get("candidates"):
            print(f"DEBUG: No candidates! Response: {json.dumps(res, indent=2)}")
        
        assert res["candidates"][0]["label"] == "dense"
        print(f"PASS: Dense identified. Top sim={res['candidates'][0]['similarity']}")

        # B) Match against 'sparse' 
        query_sparse = [1.0] + [0.0]*511
        resp = client.post("/infer/", json={"embedding": query_sparse})
        res = resp.json()
        assert res["candidates"][0]["label"] == "sparse"
        print(f"PASS: Sparse identified. Top sim={res['candidates'][0]['similarity']}")

    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    print("=== Hybrid Inference System Tests ===")
    test_inference_logic()
    print("\nAll hybrid inference tests passed.")
