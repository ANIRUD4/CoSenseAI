import cv2
import numpy as np
import os
from perception.preprocessor import Preprocessor

def create_synthetic_image(sharp_region_rect=None, total_size=(500, 500), blur_kernel=(25, 25), soft_kernel=None):
    """
    Creates a synthetic image with an optional sharp region in a sea of blur.
    sharp_region_rect: (x0, y0, x1, y1)
    soft_kernel: if provided, blur the sharp region by this much.
    """
    # 1. Create a base image with a pattern
    base = np.zeros((total_size[1], total_size[0], 3), dtype=np.uint8)
    # Draw a grid/checkerboard pattern
    for y in range(0, total_size[1], 20):
        for x in range(0, total_size[0], 20):
            if (x // 20 + y // 20) % 2 == 0:
                cv2.rectangle(base, (x, y), (x+20, y+20), (255, 255, 255), -1)
    
    if sharp_region_rect is None:
        # Heavily blur everything
        return cv2.GaussianBlur(base, blur_kernel, 0)
    
    # 2. Blur the background
    blurred = cv2.GaussianBlur(base, blur_kernel, 0)
    
    # 3. Paste the 'sharp' (or 'soft') region back in
    x0, y0, x1, y1 = sharp_region_rect
    region = base[y0:y1, x0:x1]
    if soft_kernel:
        region = cv2.GaussianBlur(region, soft_kernel, 0)
    
    blurred[y0:y1, x0:x1] = region
    
    return blurred

def test_sharp_focus():
    print("\n--- Testing Sharp Focus Detection ---")
    pre = Preprocessor()
    
    # Place sharp region in top-left tile area
    # Image is 500x500, Grid is 5x5 -> Tile is 100x100
    sharp_rect = (50, 50, 150, 150) 
    frame = create_synthetic_image(sharp_region_rect=sharp_rect)
    
    result = pre.process(frame, use_focus_roi=True)
    
    print(f"ROI Mode: {result['roi_mode']}")
    print(f"Focus Hint: {result['focus_hint']}")
    
    if result['roi_mode'] == 'focus':
        print("SUCCESS: Sharp region correctly detected as 'focus' ROI.")
    else:
        print("FAILURE: Sharp region NOT detected (or fallback triggered).")

def test_blur_fallback():
    print("\n--- Testing Blur Fallback ---")
    pre = Preprocessor()
    
    # Create a fully blurred image
    frame = create_synthetic_image(sharp_region_rect=None, blur_kernel=(51, 51))
    
    result = pre.process(frame, use_focus_roi=True)
    
    print(f"ROI Mode: {result['roi_mode']}")
    print(f"Focus Hint: {result['focus_hint']}")
    
    if result['roi_mode'] == 'center_fallback' and result['focus_hint'] is not None:
        print("SUCCESS: Blurry image correctly triggered 'center_fallback' and hint.")
    else:
        print(f"FAILURE: Blurry image did NOT trigger expected fallback/hint. Mode: {result['roi_mode']}")

def test_soft_focus_edge_fallback():
    print("\n--- Testing Soft Focus Edge Fallback ---")
    pre = Preprocessor()
    
    # Create an image that is soft enough to fail focus check
    sharp_rect = (150, 150, 250, 250)
    frame = create_synthetic_image(
        sharp_region_rect=sharp_rect, 
        blur_kernel=(101, 101),
        soft_kernel=(61, 61)
    )
    
    # Verify Laplacian variance first to be sure it's low
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    patch = gray[150:250, 150:250]
    var = cv2.Laplacian(patch, cv2.CV_64F).var()
    print(f"!!! DEBUG: PATCH VARIANCE = {var:.2f} !!!")
    
    result = pre.process(frame, use_focus_roi=True)
    
    print(f"!!! RESULT ROI MODE: {result['roi_mode']} !!!")
    print(f"FOCUS HINT: {result['focus_hint']}")
    
    if result['roi_mode'] == 'edge_fallback':
        print("SUCCESS: Soft focus correctly fell back to 'edge_fallback'.")
    else:
        print(f"FAILURE: Expected 'edge_fallback', got '{result['roi_mode']}'.")

if __name__ == "__main__":
    test_sharp_focus()
    test_blur_fallback()
    test_soft_focus_edge_fallback()
