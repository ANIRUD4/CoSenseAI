"""
scripts/verify_accuracy.py (V3 - Robust)
"""

import sys
import os
import cv2
import numpy as np
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from perception.preprocessor import Preprocessor
from perception.embedding_engine import EmbeddingEngine
from backend.utils.diversity import extract_centroids, _cosine_distance

def main():
    print("🚀 Initializing Upgraded Multi-Tier Vision Engine...")
    try:
        proc = Preprocessor()
        engine = EmbeddingEngine()
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    collector_dir = Path("data/collector")
    output_dir = Path("data/verification_results")
    output_dir.mkdir(exist_ok=True)

    # 1. Group images by label
    image_files = list(collector_dir.glob("*.jpg"))
    if not image_files:
        print("❌ No images found in data/collector")
        return

    data_map = {}
    for img_path in image_files:
        label = img_path.name.split("_")[0]
        if label not in data_map:
            data_map[label] = []
        data_map[label].append(img_path)

    print(f"Found labels: {list(data_map.keys())}")

    # 2. Benchmark specific labels
    test_label = "rubiks cube"
    if test_label not in data_map:
        test_label = list(data_map.keys())[0]

    print(f"\n--- Benchmarking '{test_label}' ---")
    imgs = data_map[test_label]
    
    learn_pool = imgs[:3]
    test_pool = imgs[3:]

    print(f"Learning from {len(learn_pool)} images...")
    learn_embeddings = []
    for i, p in enumerate(learn_pool):
        print(f"  Step 2.{i}: Processing {p.name}")
        frame = cv2.imread(str(p))
        if frame is None:
            print(f"    ⚠️ Failed to read {p}")
            continue

        try:
            res = proc.process(frame, isolate_object=True)
            processed = res["frame"]
            print(f"    ✓ rembg isolation done. Shape: {processed.shape}")
            
            # Save for visual audit
            cv2.imwrite(str(output_dir / f"audit_isolated_{test_label}_{i}.png"), (processed * 255).astype(np.uint8))
            
            emb_res = engine.get_embedding(processed)
            emb = emb_res["vector"]
            learn_embeddings.append(emb)
            print(f"    ✓ Embedding extracted ({len(emb)}d)")
        except Exception as ex:
            print(f"    ❌ Error processing {p.name}: {ex}")

    if not learn_embeddings:
        print("❌ No embeddings collected for learning.")
        return

    # Extract Centroids
    centroids = extract_centroids(learn_embeddings, n_centroids=2)
    print(f"Success: Consolidated {len(learn_pool)} raw frames into {len(centroids)} clean Centroids.")

    # 3. Test Inference
    print(f"\nRunning Inference on {len(test_pool)} test images...")
    results = []
    for p in test_pool:
        frame = cv2.imread(str(p))
        if frame is None: continue

        res = proc.process(frame, use_focus_roi=True)
        processed = res["frame"]
        
        emb_res = engine.get_embedding(processed)
        emb = emb_res["vector"]
        
        scores = [1.0 - _cosine_distance(emb, c) for c in centroids]
        max_score = max(scores)
        results.append(max_score)
        print(f"  Result for {p.name}: {max_score:.4f} similarity")

    if results:
        avg_score = sum(results) / len(results)
        print(f"\nAverage Accuracy Score for '{test_label}': {avg_score:.4f}")
    else:
        print("\nNo results for inference.")

    # 4. Cross-testing
    other_labels = [l for l in data_map.keys() if l != test_label]
    if other_labels:
        other_label = other_labels[0]
        print(f"\nCross-testing against '{other_label}' (Should be LOW similarity)...")
        neg_p = data_map[other_label][0]
        neg_frame = cv2.imread(str(neg_p))
        if neg_frame is not None:
            res = proc.process(neg_frame, use_focus_roi=True)
            neg_proc = res["frame"]
            neg_emb = engine.get_embedding(neg_proc)["vector"]
            neg_scores = [1.0 - _cosine_distance(neg_emb, c) for c in centroids]
            print(f"  Negative match '{other_label}' -> '{test_label}': {max(neg_scores):.4f}")

    print(f"\nAudit results (masked images) saved to: {output_dir}")

if __name__ == "__main__":
    main()
