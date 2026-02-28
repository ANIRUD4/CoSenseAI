from perception.camera import CameraStream

_camera = CameraStream(src=0).start()

def get_frame_fn():
    """
    Returns a single NumPy frame (BGR).
    """
    return _camera.get_frame()
