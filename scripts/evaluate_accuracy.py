import os
import cv2
import numpy as np
import time
from collections import defaultdict

import sys
sys.path.append(os.getcwd())

from backend.routes.infer import infer_object
from backend.schemas.inference import InferRequest
from perception.interface import get_embedding

def calculate_metrics(y_true, y_pred):
    classes = set(y_true).union(set(y_pred))
    
    metrics = {}
    correct = 0
    total = len(y_true)
    
    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics[cls] = {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
        
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / total if total > 0 else 0
    
    return accuracy, metrics

def evaluate_accuracy(dataset_dir="dataset"):
    if not os.path.exists(dataset_dir):
        print(f"Dataset directory '{dataset_dir}' not found.")
        print("Please structure it as dataset/<class_name>/<image_files>")
        return
        
    print(f"Evaluating accuracy on dataset: {dataset_dir}")
    
    y_true = []
    y_pred = []
    
    start_time = time.time()
    
    for class_name in os.listdir(dataset_dir):
        class_dir = os.path.join(dataset_dir, class_name)
        if not os.path.isdir(class_dir):
            continue
            
        for img_name in os.listdir(class_dir):
            img_path = os.path.join(class_dir, img_name)
            
            img = cv2.imread(img_path)
            if img is None:
                print(f"Failed to read image: {img_path}")
                continue
                
            try:
                # Get embedding with center ROI enabled for testing
                emb = get_embedding(img, use_center_roi=True)
                
                # Run inference
                req = InferRequest(embedding=emb)
                result = infer_object(req)
                
                # The prediction is in candidates[0] if confident
                if result.get("candidates") and len(result["candidates"]) > 0:
                    predicted_class = result["candidates"][0]["id"]
                else:
                    predicted_class = "unknown"
                    
                y_true.append(class_name.lower())
                y_pred.append(predicted_class.lower())
                
                print(f"Processed {class_name}/{img_name} -> Predicted: {predicted_class}")
                
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                
    end_time = time.time()
    
    if not y_true:
        print("No valid images processed.")
        return
        
    # Calculate metrics
    accuracy, metrics_per_class = calculate_metrics(y_true, y_pred)
    
    print("\n" + "="*40)
    print("EVALUATION RESULTS")
    print("="*40)
    print(f"Total Images: {len(y_true)}")
    print(f"Time Taken: {end_time - start_time:.2f}s")
    print(f"Overall Accuracy: {accuracy * 100:.2f}%")
    print("-" * 40)
    
    print(f"{'Class':<20} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 60)
    for cls, mets in metrics_per_class.items():
        if cls in set(y_true): # Only print metrics for actual classes in dataset
            print(f"{cls[:18]:<20} | {mets['precision']:.4f}     | {mets['recall']:.4f}   | {mets['f1']:.4f}")
    
    # Return metrics for programmatic usage
    return accuracy, metrics_per_class

if __name__ == "__main__":
    import sys
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    evaluate_accuracy(dataset_path)
