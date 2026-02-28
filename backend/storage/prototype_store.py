import json
import os
from typing import Dict, List
import time
import numpy as np

STORE_PATH = "data/prototypes.json"

def compute_cosine_sim(a, b) -> float:
    a = np.array(a)
    b = np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0: return 0.0
    return float(np.dot(a, b) / denom)

def load_prototypes() -> Dict:
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH, "r") as f:
        return json.load(f)

def save_prototypes(data: Dict):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)

def add_prototype(label: str, embedding: list[float], action: str = None, dist_threshold: float = 0.85):
    """
    Smart Add: Either updates existing close prototype or adds new one.
    This creates multiple 'centroids' for high-variance objects.
    """
    data = load_prototypes()

    if label not in data:
        data[label] = {"prototypes": []}
    
    protos = data[label]["prototypes"]
    
    # Check if there's a close existing prototype (Multi-Centroid Logic)
    closest_idx = -1
    best_sim = -1.0
    
    for i, p in enumerate(protos):
        sim = compute_cosine_sim(embedding, p["vector"])
        if sim > best_sim:
            best_sim = sim
            closest_idx = i
            
    if closest_idx != -1 and best_sim >= dist_threshold:
        # Update existing (merging into centroid)
        p = protos[closest_idx]
        alpha = 0.2
        p["vector"] = [(1 - alpha) * old + alpha * new for old, new in zip(p["vector"], embedding)]
        p["uses"] += 1
        p["last_updated"] = time.time()
        if action and not p.get("action"):
            p["action"] = action
    else:
        # Add as new prototype (new centroid)
        protos.append({
            "vector": embedding,
            "weight": 1.0,
            "uses": 1,
            "action": action,
            "last_updated": time.time()
        })

    save_prototypes(data)

def update_prototype(label: str, idx: int, embedding: list[float], alpha: float = 0.2, confidence: float = 0.5):
    data = load_prototypes()
    if label not in data or idx >= len(data[label]["prototypes"]):
        return

    proto = data[label]["prototypes"][idx]
    old_vec = proto["vector"]
    new_vec = [(1 - alpha) * p + alpha * e for p, e in zip(old_vec, embedding)]

    proto["vector"] = new_vec
    proto["uses"] += 1
    
    base_boost = 0.15
    boost = base_boost * max(confidence, 0.3)
    proto["weight"] = min(proto["weight"] + boost, 2.0)
    proto["last_updated"] = time.time()

    save_prototypes(data)
