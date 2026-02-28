import cv2
import numpy as np

class Preprocessor:
    """
    Prepares image for embedding extraction.
    Includes background removal for better object isolation.
    """

    def __init__(self, target_size=(224, 224)):
        self.target_size = target_size
        self.back_sub = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=16, detectShadows=True)

    def process(self, frame, isolate_object=False, use_center_roi=False, roi_ratio=0.6):
        """
        Resize + normalize + optional isolation + optional center ROI.
        """
        processed_frame = frame
        
        if use_center_roi:
            h, w = processed_frame.shape[:2]
            roi_h = int(h * roi_ratio)
            roi_w = int(w * roi_ratio)
            y_start = (h - roi_h) // 2
            y_end = y_start + roi_h
            x_start = (w - roi_w) // 2
            x_end = x_start + roi_w
            processed_frame = processed_frame[y_start:y_end, x_start:x_end]

        # Resize first
        resized = cv2.resize(processed_frame, self.target_size)
        
        if isolate_object:
            # Mask out background
            mask = self.back_sub.apply(resized)
            # Dilate to fill holes
            mask = cv2.dilate(mask, None, iterations=2)
            # Apply mask to image
            isolated = cv2.bitwise_and(resized, resized, mask=mask)
            resized = isolated

        normalized = resized.astype(np.float32) / 255.0
        return normalized
