import os
import cv2
import sys

# Ensure we can import from project root
sys.path.append(os.getcwd())

from perception.interface import get_embedding
from backend.storage.prototype_store import add_prototype

def teach_from_dataset(dataset_dir="dataset"):
    if not os.path.exists(dataset_dir):
        print(f"Dataset directory '{dataset_dir}' not found.")
        return

    print(f"Teaching objects from dataset: {dataset_dir}")

    for class_name in os.listdir(dataset_dir):
        class_dir = os.path.join(dataset_dir, class_name)
        if not os.path.isdir(class_dir):
            continue

        print(f"Learning class: {class_name}")
        
        count = 0
        for img_name in os.listdir(class_dir):
            img_path = os.path.join(class_dir, img_name)
            
            img = cv2.imread(img_path)
            if img is None:
                print(f"  Failed to read image: {img_path}")
                continue
                
            try:
                # 1. Extract embedding (matching the learning flow)
                emb = get_embedding(img, use_center_roi=True)
                
                # 2. Add as prototype
                add_prototype(class_name.lower(), emb)
                count += 1
                print(f"  Added prototype from {img_name}")

            except Exception as e:
                print(f"  Error processing {img_path}: {e}")

        print(f"Finished learning '{class_name}'. Total prototypes added: {count}")

if __name__ == "__main__":
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    teach_from_dataset(dataset_path)
