import os
import json
import time
import cv2
import numpy as np

COLLECTOR_DIR = "data/collector"

def save_collected_data(image: np.ndarray, label: str, bbox: dict | None):
    """
    Saves a raw image and its annotation to the collector directory.
    bbox: {x, y, w, h} as normalized floats.
    """
    if not os.path.exists(COLLECTOR_DIR):
        os.makedirs(COLLECTOR_DIR, exist_ok=True)
        
    timestamp = int(time.time() * 1000)
    filename = f"{label}_{timestamp}"
    
    # Save Image
    image_path = os.path.join(COLLECTOR_DIR, f"{filename}.jpg")
    cv2.imwrite(image_path, image)
    
    # Save Annotation
    annotation = {
        "label": label,
        "bbox": bbox,
        "timestamp": timestamp,
        "image_file": f"{filename}.jpg"
    }
    
    json_path = os.path.join(COLLECTOR_DIR, f"{filename}.json")
    with open(json_path, 'w') as f:
        json.dump(annotation, f, indent=4)
        
    print(f"COLLECTOR: Saved data for '{label}' to {image_path}")
