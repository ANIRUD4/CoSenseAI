import cv2
import threading
import time
from typing import Optional
import numpy as np

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            raise RuntimeError("Camera not working")

    def capture_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Could not read frame")
        return frame

    def close(self):
        self.cap.release()

class CameraStream:
    """
    Threaded camera stream that always keeps the latest frame ready.
    Good for real-time inference/learning.
    """
    def __init__(self, src: int = 0, width: int = 640, height: int = 480):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self._frame: Optional[np.ndarray] = None
        self._running = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        return self

    def _update_loop(self):
        while self._running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self._frame = frame
            time.sleep(0.01)  # reduce CPU usage

    def get_frame(self) -> np.ndarray:
        with self._lock:
            if self._frame is None:
                raise ValueError("Camera frame not ready yet")
            return self._frame.copy()

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
