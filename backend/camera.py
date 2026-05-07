import cv2
import threading
import time

class CameraStream:
    def __init__(self):
        self.video = None
        self.lock = threading.Lock()
        self.frame = None
        self.running = False
        self.thread = None

    def start(self):
        """Starts the background camera capture thread."""
        if self.running:
            return
            
        self.running = True
        # Initialize video capture. On Pi, this grabs the default USB or CSI camera.
        # Force CAP_V4L2 to ensure OpenCV only takes the video node and doesn't use GStreamer
        # which might accidentally lock the ALSA audio node!
        self.video = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        # Set a reasonable resolution to match the frontend expectations
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video.set(cv2.CAP_PROP_FPS, 30)

        # Start background thread
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _update_loop(self):
        while self.running:
            if self.video is None or not self.video.isOpened():
                time.sleep(0.1)
                continue

            success, image = self.video.read()
            if success:
                # Rotate 90 degrees counter-clockwise to align with GUI
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Encode as JPEG
                ret, jpeg = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    with self.lock:
                        self.frame = jpeg.tobytes()
            else:
                print("Failed to grab camera frame. Retrying...")
                time.sleep(0.5)

    def stop(self):
        """Stops the camera and releases hardware."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.video:
            self.video.release()
            self.video = None

    def get_frame(self):
        """Yields the latest JPEG frame infinitely for MJPEG streaming."""
        while True:
            with self.lock:
                frame = self.frame
            
            if frame is None:
                # Provide a blank placeholder if camera isn't ready
                # This prevents the stream from crashing instantly
                # Rotated dimension: 480 width, 640 height
                blank = cv2.imencode('.jpg', cv2.Mat(640, 480, cv2.CV_8UC3, (0, 0, 0)))[1].tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + blank + b'\r\n')
                time.sleep(0.1)
                continue

            # MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # Throttle slightly to prevent flooding (approx 30fps max)
            time.sleep(0.033)

# Global singleton instance
camera_stream = CameraStream()
