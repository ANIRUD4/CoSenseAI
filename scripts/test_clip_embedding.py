"""
scripts/test_clip_embedding.py

Verifies the 3-tier CLIP → TFLite → CV embedding engine.

Run from project root:
    python -m scripts.test_clip_embedding
"""

import sys
import os
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from perception.embedding_engine import EmbeddingEngine, CLIP_EMBEDDING_DIM


def make_dummy_image(seed: int = 0) -> np.ndarray:
    """224×224×3 float32 [0, 1] image (random noise, different per seed)."""
    rng = np.random.default_rng(seed)
    return rng.random((224, 224, 3)).astype(np.float32)


def test_embedding_shape_and_norm():
    engine = EmbeddingEngine()
    img    = make_dummy_image(seed=1)
    emb    = engine.get_embedding(img, normalize=True)

    assert isinstance(emb, list), "Embedding must be a list"
    assert len(emb) > 0, "Embedding must not be empty"

    arr  = np.array(emb, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    assert abs(norm - 1.0) < 1e-4, f"L2 norm should be ~1.0, got {norm:.6f}"

    if engine.active_engine == "clip":
        assert len(emb) == CLIP_EMBEDDING_DIM, (
            f"CLIP should produce {CLIP_EMBEDDING_DIM}-d, got {len(emb)}"
        )
        print(f"PASS: CLIP embedding shape={len(emb)}, norm={norm:.6f}")
    else:
        print(
            f"INFO: CLIP not available, active engine='{engine.active_engine}' "
            f"dim={len(emb)}, norm={norm:.6f}"
        )


def test_two_different_images_differ():
    """Two visually different images should have cosine similarity < 0.99."""
    engine = EmbeddingEngine()
    emb1 = np.array(engine.get_embedding(make_dummy_image(seed=42)))
    emb2 = np.array(engine.get_embedding(make_dummy_image(seed=99)))

    cos_sim = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8))
    print(f"Cosine similarity between two random images: {cos_sim:.4f}")
    assert cos_sim < 0.99, f"Random images should differ; got sim={cos_sim:.4f}"
    print("PASS: Two random images produce distinct embeddings.")


def test_same_image_reproducible():
    """Same image through same engine yields identical embedding."""
    engine = EmbeddingEngine()
    img  = make_dummy_image(seed=7)
    emb1 = engine.get_embedding(img, normalize=True)
    emb2 = engine.get_embedding(img, normalize=True)
    assert emb1 == emb2, "Same image should produce identical embedding"
    print("PASS: Embedding is deterministic for same input.")


if __name__ == "__main__":
    print("=== CLIP / Embedding Engine Tests ===")
    test_embedding_shape_and_norm()
    test_two_different_images_differ()
    test_same_image_reproducible()
    print("\nAll embedding tests passed.")
