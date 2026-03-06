"""
scripts/migrate_negatives.py

Cleans up data/hard_negatives.json by removing vectors that don't match 
the current system dimension (512 for CLIP).
"""
import sys, os, json
from typing import Dict, List

# Add parent dir to path to import store
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NEGATIVE_STORE_PATH = "data/hard_negatives.json"
EXPECTED_DIM = 512

def migrate():
    if not os.path.exists(NEGATIVE_STORE_PATH):
        print("No hard_negatives.json found. Nothing to migrate.")
        return

    with open(NEGATIVE_STORE_PATH, "r") as f:
        data = json.load(f)

    cleaned_data = {}
    removed_count = 0
    total_count = 0

    for label, negatives in data.items():
        valid_negs = []
        for neg in negatives:
            total_count += 1
            vector = neg.get("vector", [])
            if len(vector) == EXPECTED_DIM:
                valid_negs.append(neg)
            else:
                removed_count += 1
        
        if valid_negs:
            cleaned_data[label] = valid_negs

    if removed_count > 0:
        with open(NEGATIVE_STORE_PATH, "w") as f:
            json.dump(cleaned_data, f, indent=2)
        print(f"MIGRATION COMPLETE:")
        print(f" - Scanned {total_count} negatives.")
        print(f" - Removed {removed_count} stale negatives with dimension mismatch.")
        print(f" - Retained {total_count - removed_count} valid negatives.")
    else:
        print(f"MIGRATION SKIPPED: All {total_count} negatives already match dimension {EXPECTED_DIM}.")

if __name__ == "__main__":
    migrate()
