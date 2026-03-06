"""
scripts/test_prototype_mean.py

Verifies that:
  1. add_prototype() correctly computes and caches mean_vector.
  2. get_mean_vector() returns None for unknown labels.
  3. Cached mean matches hand-computed numpy mean.

Run from project root:
    python -m scripts.test_prototype_mean
"""

import sys, os, json, tempfile, shutil, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

# Patch STORE_PATH to a temp file so we don't touch real data
import backend.storage.prototype_store as ps

_orig_store = ps.STORE_PATH


def _patch_store(tmp_dir):
    ps.STORE_PATH = os.path.join(tmp_dir, "test_prototypes.json")


def _restore_store():
    ps.STORE_PATH = _orig_store


def test_mean_vector_computed():
    tmp = tempfile.mkdtemp()
    _patch_store(tmp)

    try:
        vecs = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]

        for v in vecs:
            ps.add_prototype("test_label", v)

        data = ps.load_prototypes()
        mean_vec = data["test_label"].get("mean_vector")

        assert mean_vec is not None, "mean_vector should be present after 3 adds"

        # Hand-compute expected mean
        raw_mean = np.mean([np.array(v) for v in vecs], axis=0).astype(np.float32)
        norm     = np.linalg.norm(raw_mean)
        expected = (raw_mean / norm).tolist() if norm > 0 else raw_mean.tolist()

        for a, b in zip(mean_vec, expected):
            assert abs(a - b) < 1e-5, f"mean_vector mismatch: {a:.6f} vs {b:.6f}"

        # Also check via helper
        mv = ps.get_mean_vector("test_label")
        assert mv is not None, "get_mean_vector() should return a vector"
        print(f"PASS: mean_vector computed correctly ({len(mean_vec)}-d)")

    finally:
        _restore_store()
        shutil.rmtree(tmp)


def test_get_mean_unknown_label():
    tmp = tempfile.mkdtemp()
    _patch_store(tmp)
    try:
        mv = ps.get_mean_vector("nonexistent")
        assert mv is None, "get_mean_vector() should return None for unknown label"
        print("PASS: get_mean_vector() returns None for unknown label.")
    finally:
        _restore_store()
        shutil.rmtree(tmp)


def test_recompute_all_means():
    tmp = tempfile.mkdtemp()
    _patch_store(tmp)
    try:
        # Write raw prototypes without mean_vector (simulates old schema)
        raw = {
            "cup": {
                "prototypes": [
                    {"vector": [1.0, 0.0], "weight": 1.0, "uses": 1, "last_updated": 0},
                    {"vector": [0.0, 1.0], "weight": 1.0, "uses": 1, "last_updated": 0},
                ]
            }
        }
        ps.save_prototypes(raw)

        ps.recompute_all_means()

        data = ps.load_prototypes()
        assert "mean_vector" in data["cup"], "recompute_all_means() should add mean_vector"
        print("PASS: recompute_all_means() works on old schema (no mean_vector).")
    finally:
        _restore_store()
        shutil.rmtree(tmp)


if __name__ == "__main__":
    print("=== Prototype Mean Vector Tests ===")
    test_mean_vector_computed()
    test_get_mean_unknown_label()
    test_recompute_all_means()
    print("\nAll prototype mean tests passed.")
