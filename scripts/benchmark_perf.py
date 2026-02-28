import time
import numpy as np
import cv2
import sys
import os

# Ensure we can import from project root
sys.path.append(os.getcwd())

from perception.preprocessor import Preprocessor
from perception.embedding_engine import EmbeddingEngine

def benchmark():
    print("--- IntelShareAI Performance Benchmark ---")
    
    # 1. Setup
    prep = Preprocessor()
    engine = EmbeddingEngine()
    
    # Create dummy frame (HD)
    dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    print(f"Target Size: {prep.target_size}")
    
    # 2. Measure Preprocessing
    start = time.time()
    processed = prep.process(dummy_frame)
    end = time.time()
    print(f"Preprocessing Time: {(end - start) * 1000:.2f}ms")
    
    # 3. Measure Embedding Extraction
    start = time.time()
    embedding = engine.get_embedding(processed)
    end = time.time()
    
    print(f"Embedding Time: {(end - start) * 1000:.2f}ms")
    print(f"Embedding Dimension: {len(embedding)}")
    
    # 4. Check for Deep Learning
    if engine.interpreter:
        print("Status: DEEP LEARNING ENABLED (MobileNetV3)")
    else:
        print("Status: FALLBACK ENABLED (Simple Features)")

if __name__ == "__main__":
    benchmark()
