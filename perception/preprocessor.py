import cv2
import numpy as np

# ── rembg (U²-Net background removal) ─────────────────────────────────────────
# Graceful fallback: if rembg is not installed, saliency masking is skipped.
_REMBG_AVAILABLE = False
_rembg_session = None
try:
    from rembg import remove as _rembg_remove, new_session as _rembg_new_session
    _REMBG_AVAILABLE = True
    # Load the u2netp model (lightweight variant, ~4MB) at import time for speed.
    # Alternatives: 'u2net' (larger, more accurate) or 'silueta' (fastest).
    _rembg_session = _rembg_new_session("u2netp")
    print("INFO: rembg U²-Net background removal loaded (u2netp).")
except Exception as _e:
    print(f"INFO: rembg not available ({_e}). Background masking will use MOG2 fallback.")

# ── Focus-ROI tuning knobs ─────────────────────────────────────────────────
# A tile's Laplacian variance below this means the frame is too blurry to
# trust any focus crop.  Falls back to center crop + user hint.
BLUR_THRESHOLD: float = 40.0   # lower → more tolerant of blur; 40 is a good default

# Grid size for the tiling pass (GRID x GRID tiles scanned per frame).
FOCUS_GRID: int = 5

# The focus patch is *expanded* by this factor before being used as the crop.
# E.g. 2.5 means a 40 x 40 px tile becomes a 100 x 100 crop area around its centre.
FOCUS_EXPAND: float = 2.5

# Minimum crop side length in pixels (prevents micro-crops on small tiles).
FOCUS_MIN_CROP_PX: int = 80

# ── Edge-Density ROI tuning knobs ──────────────────────────────────────────
# Threshold for Canny edge detection
EDGE_LOW_THRESHOLD: int = 50
EDGE_HIGH_THRESHOLD: int = 150
# Margin for the edge-density crop
EDGE_MARGIN: float = 0.2


class Preprocessor:
    """
    Prepares image frames for embedding extraction.

    ROI modes (applied before resize, in priority order):
    -------------------------------------------------------
    1. use_focus_roi=True    Laplacian-variance focus crop:
                             Tiles the frame, finds the sharpest patch, and
                             crops an expanded region around it.
                             Falls back to center crop if frame is too blurry,
                             and returns a 'focus_hint' message for the UI.

    2. use_saliency_roi=True Motion/background-subtraction crop around the
                             largest moving foreground object (MOG2).

    3. use_center_roi=True   Fixed center crop using roi_ratio of the frame.

    4. (neither)             Full frame forwarded to the embedding engine.

    Priority: focus_roi > saliency_roi > center_roi > full frame
    """

    def __init__(self, target_size=(224, 224)):
        self.target_size = target_size
        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=50, varThreshold=16, detectShadows=True
        )
        # ROI Stability Tracker (Pi 5 Optimization)
        self.tracker = None
        self.tracking_bbox = None # (x, y, w, h)
        self.frames_since_last_focus = 0
        self.MAX_TRACKING_FRAMES = 30 # Re-scan focus every 30 frames

    # ── Focus-based ROI ───────────────────────────────────────────────────────

    def _laplacian_variance(self, gray_patch: np.ndarray) -> float:
        """Return the Laplacian variance (sharpness measure) of a grayscale patch."""
        return float(cv2.Laplacian(gray_patch, cv2.CV_64F).var())

    def _focus_crop(self, frame) -> tuple:
        """
        Find the sharpest tile in the frame using Laplacian variance and
        return an expanded crop around it.

        Returns
        -------
        (cropped_frame, focus_hint)
            cropped_frame : np.ndarray  — the ROI crop (or center fallback)
            focus_hint    : str | None  — user-facing hint, or None if focus OK
        """
        fh, fw = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        tile_h = fh // FOCUS_GRID
        tile_w = fw // FOCUS_GRID

        best_var = -1.0
        best_cx, best_cy = fw // 2, fh // 2   # default: frame centre

        for row in range(FOCUS_GRID):
            for col in range(FOCUS_GRID):
                y0 = row * tile_h
                x0 = col * tile_w
                y1 = min(y0 + tile_h, fh)
                x1 = min(x0 + tile_w, fw)
                patch = gray[y0:y1, x0:x1]
                if patch.size == 0:
                    continue
                var = self._laplacian_variance(patch)
                if var > best_var:
                    best_var = var
                    best_cx = x0 + (x1 - x0) // 2
                    best_cy = y0 + (y1 - y0) // 2

        # If the sharpest patch is still blurry, fall back to center crop
        if best_var < BLUR_THRESHOLD:
            print(
                f"FOCUS ROI: frame too blurry (var={best_var:.1f} < {BLUR_THRESHOLD}) "
                f"-> center fallback"
            )
            center_crop = self._center_crop(frame, ratio=0.6)
            hint = (
                f"Frame is blurry (sharpness={best_var:.0f}). "
                "Please hold the camera steady and place the object in the centre."
            )
            return center_crop, hint, None

        # Expand the tile centre to a larger crop
        half = max(
            FOCUS_MIN_CROP_PX // 2,
            int(tile_h * FOCUS_EXPAND / 2),
            int(tile_w * FOCUS_EXPAND / 2),
        )
        x1c = min(fw, best_cx + half)
        x0c = max(0,  best_cx - half)
        y1c = min(fh, best_cy + half)
        y0c = max(0,  best_cy - half)

        print(
            f"FOCUS ROI: sharpest tile var={best_var:.1f} "
            f"centre=({best_cx},{best_cy}) crop=({x0c},{y0c},{x1c},{y1c})"
        )
        
        # Return the crop coordinates so we can initialize the tracker
        return frame[y0c:y1c, x0c:x1c], None, (x0c, y0c, x1c - x0c, y1c - y0c)

    # ── Edge-Density-based ROI ────────────────────────────────────────────────

    def _edge_density_crop(self, frame) -> np.ndarray:
        """
        Find the region with the highest density of edges and return a crop around it.
        This is typically more robust than Laplacian focus for fixed-focus webcams.
        """
        fh, fw = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Edge detection
        edges = cv2.Canny(gray, EDGE_LOW_THRESHOLD, EDGE_HIGH_THRESHOLD)
        
        # 2. Find contours of the edges to group them
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("EDGE ROI: No edges found, falling back to center.")
            return self._center_crop(frame)

        # 3. Find the bounding box that encompasses the most 'edge activity'
        # For simplicity, we'll take the largest contour by area or the bounding box
        # of all significant contours.
        all_points = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 50:  # noise filter
                all_points.extend(cnt)

        if not all_points:
            return self._center_crop(frame)

        x, y, w, h = cv2.boundingRect(np.array(all_points))
        
        # 4. Apply margin
        mx, my = int(w * EDGE_MARGIN), int(h * EDGE_MARGIN)
        x0 = max(0, x - mx)
        y0 = max(0, y - my)
        x1 = min(fw, x + w + mx)
        y1 = min(fh, y + h + my)

        print(f"EDGE ROI: detected bounds=({x0},{y0},{x1},{y1})")
        return frame[y0:y1, x0:x1]

    # ── Neural background removal (rembg / U²-Net saliency) ─────────────────

    def _rembg_isolate(self, frame: np.ndarray) -> np.ndarray:
        """
        Remove the background using rembg's U²-Net model, returning a BGR
        image with the background blacked out.

        Unlike the old MOG2 approach (which required motion), this works on
        *still* objects, making it ideal for the few-shot learning flow.

        Falls back to the MOG2 saliency crop if rembg is unavailable.
        """
        if _REMBG_AVAILABLE and _rembg_session is not None:
            try:
                from PIL import Image as _PILImage
                import io as _io

                # rembg expects a PIL Image or raw bytes; convert from BGR numpy.
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_input = _PILImage.fromarray(frame_rgb)

                # Remove background — output is RGBA PIL image.
                output_pil = _rembg_remove(pil_input, session=_rembg_session)

                # Composite onto a pure black background using the alpha channel.
                bg = _PILImage.new("RGBA", output_pil.size, (0, 0, 0, 255))
                composited = _PILImage.alpha_composite(bg, output_pil)

                # Convert back to BGR numpy.
                result_rgb = np.array(composited.convert("RGB"))
                result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

                print("SALIENCY: rembg U²-Net background removed successfully.")
                return result_bgr

            except Exception as e:
                print(f"WARNING: rembg inference failed ({e}). Falling back to MOG2.")

        # ── MOG2 fallback (motion-based) ──────────────────────────────────────
        return self._saliency_mog2_crop(frame)

    def _saliency_mog2_crop(self, frame: np.ndarray, margin: float = 0.15) -> np.ndarray:
        """
        Legacy MOG2 motion-based fallback for when rembg is unavailable.
        Find the largest moving contour via background subtraction and
        return a cropped sub-image around it.
        Falls back to the full frame if no meaningful contour is found.
        """
        fg_mask = self.back_sub.apply(frame)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        fg_mask = cv2.dilate(fg_mask, None, iterations=3)

        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return frame

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 200:
            return frame

        x, y, w, h = cv2.boundingRect(largest)
        fh, fw = frame.shape[:2]
        mx, my = int(w * margin), int(h * margin)
        x1 = min(fw, x + w + mx)
        x0 = max(0,  x - mx)
        y1 = min(fh, y + h + my)
        y0 = max(0,  y - my)

        print(f"SALIENCY MOG2: crop=({x0},{y0},{x1},{y1}) on ({fw}x{fh}) frame")
        return frame[y0:y1, x0:x1]

    # ── Center crop helper ────────────────────────────────────────────────────

    def _center_crop(self, frame, ratio: float = 0.6):
        h, w = frame.shape[:2]
        roi_h = int(h * ratio)
        roi_w = int(w * ratio)
        y0 = (h - roi_h) // 2
        x0 = (w - roi_w) // 2
        return frame[y0:y0 + roi_h, x0:x0 + roi_w]

    def _manual_crop(self, frame: np.ndarray, bbox: dict) -> np.ndarray:
        """
        Crop the frame based on a client-provided bounding box.
        bbox components (x, y, w, h) are expected as normalized floats [0, 1].
        """
        fh, fw = frame.shape[:2]
        
        # Convert normalized [0, 1] to pixel coordinates
        x = int(bbox.get("x", 0) * fw)
        y = int(bbox.get("y", 0) * fh)
        w = int(bbox.get("w", 1) * fw)
        h = int(bbox.get("h", 1) * fh)
        
        # Ensure within bounds
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(fw, x + w)
        y1 = min(fh, y + h)
        
        if x1 <= x0 or y1 <= y0:
            print(f"MANUAL ROI: Invalid bbox {bbox}, falling back to full frame.")
            return frame
            
        print(f"MANUAL ROI: crop=({x0},{y0},{x1},{y1}) from normalized {bbox}")
        return frame[y0:y1, x0:x1]

    # ── Main processing entry point ───────────────────────────────────────────

    def process(
        self,
        frame,
        isolate_object: bool = False,
        use_focus_roi: bool = False,
        use_edge_roi: bool = False,
        use_saliency_roi: bool = False,
        use_center_roi: bool = False,
        manual_bbox: dict | None = None,
        roi_ratio: float = 0.6,
    ) -> dict:
        """
        Resize + normalize + optional ROI selection.

        Returns
        -------
        dict with keys:
            "frame"       : np.ndarray (float32, normalised to [0, 1])
            "focus_hint"  : str | None — non-None when the frame was blurry and
                            the user should be told to hold the camera steady.
            "roi_mode"    : str — which ROI mode was actually used.
        """
        processed_frame = frame
        focus_hint = None
        roi_mode = "full_frame"

        if manual_bbox:
            processed_frame = self._manual_crop(processed_frame, manual_bbox)
            roi_mode = "manual"
            
        elif use_focus_roi:
            # ── ROI Stability Logic (Pi 5) ──
            need_new_focus = (
                self.tracker is None or 
                self.frames_since_last_focus >= self.MAX_TRACKING_FRAMES
            )
            
            if not need_new_focus:
                success, bbox = self.tracker.update(frame)
                if success:
                    x, y, w, h = [int(v) for v in bbox]
                    # Ensure bbox is within frame
                    fh, fw = frame.shape[:2]
                    x0, y0 = max(0, x), max(0, y)
                    x1, y1 = min(fw, x + w), min(fh, y + h)
                    
                    if (x1 - x0) > 20 and (y1 - y0) > 20:
                        processed_frame = frame[y0:y1, x0:x1]
                        roi_mode = "tracked_focus"
                        self.frames_since_last_focus += 1
                    else:
                        need_new_focus = True # Bbox too small or invalid
                else:
                    need_new_focus = True # Tracker lost object

            if need_new_focus:
                # Reset tracker and find focus again
                self.tracker = None 
                processed_frame, focus_hint, bbox_coords = self._focus_crop(processed_frame)
                roi_mode = "center_fallback" if focus_hint else "focus"
                
                if not focus_hint and bbox_coords:
                    # Initialize tracker for subsequent frames
                    print("DEBUG: Initializing tracker with new try-except fallback logic...")
                    try:
                        self.tracker = cv2.TrackerKCF_create()
                        print("DEBUG: Successfully created TrackerKCF")
                    except AttributeError:
                        print("DEBUG: TrackerKCF not in cv2, trying cv2.legacy...")
                        try:
                            self.tracker = cv2.legacy.TrackerKCF_create()
                            print("DEBUG: Successfully created legacy.TrackerKCF")
                        except AttributeError:
                            print("DEBUG: legacy.TrackerKCF failed, falling back to MIL...")
                            self.tracker = cv2.TrackerMIL_create()
                        
                    self.tracker.init(frame, bbox_coords)
                    self.frames_since_last_focus = 0
                    roi_mode = "focus_init_tracking"

                # 🔥 Laptop Webcam Optimization: If focus ROI failed due to blur, 
                # try Edge-Density ROI before giving up.
                if focus_hint:
                    print(f"FOCUS ROI failed (blur), attempting EDGE ROI fallback...")
                    edge_frame = self._edge_density_crop(frame) 
                    processed_frame = edge_frame
                    roi_mode = "edge_fallback"
                    focus_hint = None 
        
        elif use_edge_roi:
            processed_frame = self._edge_density_crop(processed_frame)
            roi_mode = "edge_density"

        elif use_saliency_roi:
            processed_frame = self._rembg_isolate(processed_frame)
            roi_mode = "saliency_rembg" if _REMBG_AVAILABLE else "saliency_mog2"

        elif use_center_roi:
            processed_frame = self._center_crop(processed_frame, ratio=roi_ratio)
            roi_mode = "center"

        resized = cv2.resize(processed_frame, self.target_size)

        if isolate_object:
            # ── Use rembg for high-quality static-object isolation ────────────
            # In learning flows the object is typically held still, so MOG2
            # (motion-based) would produce an empty mask.  rembg works on
            # single frames without any temporal context.
            isolated = self._rembg_isolate(resized)
            resized = isolated

        return {
            "frame": resized.astype(np.float32) / 255.0,
            "focus_hint": focus_hint,
            "roi_mode": roi_mode,
        }
