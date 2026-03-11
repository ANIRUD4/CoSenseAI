import os
import cv2
import sys
from backend.llm_augment import augment_with_web_images

def test_pipeline():
    label = "blue square"
    image_path = "test_image.jpg"
    
    print(f"Testing LLM Augmentation Pipeline")
    print(f"Label: {label}")
    print(f"Image Path: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"Error: Could not find image at {image_path}")
        sys.exit(1)
        
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Failed to load image at {image_path}")
        sys.exit(1)
        
    print("\n--- Starting Augmentation ---")
    try:
        embeddings = augment_with_web_images(label, img, max_web_images=3)
        print("\n--- Augmentation Complete ---")
        print(f"Total embeddings generated: {len(embeddings)}")
        if embeddings:
            print(f"Shape of first embedding: {len(embeddings[0])}")
            print("Successfully tested pipeline!")
        else:
            print("Warning: Pipeline returned empty embeddings list.")
    except Exception as e:
        print(f"Error during pipeline execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
