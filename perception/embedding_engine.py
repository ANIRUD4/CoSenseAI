import cv2
import numpy as np
import os

class EmbeddingEngine:
    """
    Extracts semantic visual embeddings using Deep Learning.
    Uses MobileNetV3-Small optimized for Raspberry Pi.
    """

    def __init__(self, model_path="models/mobilenet_v3_small_quant.tflite"):
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        
        # Deferred import to handle environment-specific issues
        tflite = None
        import platform
        is_windows = platform.system() == "Windows"
        
        try:
            # Production (Pi) usually has tflite_runtime
            import tflite_runtime.interpreter as _tflite
            tflite = _tflite
        except:
            # On Windows, tensorflow.lite often has Protobuf version conflicts
            # and is very heavy. Only try if not on Windows or if specifically needed.
            # Here we skip it on Windows to avoid the 'MessageFactory' AttributeError.
            if not is_windows:
                try:
                    import tensorflow.lite as _tflite
                    tflite = _tflite
                except:
                    tflite = None
            else:
                tflite = None
        
        if tflite is not None and os.path.exists(self.model_path):
            try:
                self.interpreter = tflite.Interpreter(model_path=self.model_path)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
            except Exception as e:
                print(f"WARNING: Failed to initialize TFLite interpreter: {e}")
        else:
            if tflite is None:
                print("WARNING: TFLite not installed. Falling back to simple features.")
            if not os.path.exists(self.model_path):
                print(f"WARNING: Model file not found at {self.model_path}. Falling back to simple features.")

    def get_embedding(self, image):
        """
        image: preprocessed image (224x224x3)
        returns: List[float]
        """
        
        # If we have a working TFLite interpreter, use Deep Learning
        if self.interpreter:
            try:
                # Prepare input tensor
                input_data = np.expand_dims(image, axis=0).astype(np.float32)
                
                # MobileNetV3 typically expects [0, 255] for quantized or [0, 1] for float
                # Preprocessor already does / 255.0, so this is float [0, 1]
                
                self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
                self.interpreter.invoke()
                
                # Extract features from the final layer before the head
                # For feature extraction models, this is often the only output
                embedding = self.interpreter.get_tensor(self.output_details[0]['index'])
                
                # Squeeze to 1D and convert to list
                return embedding.flatten().tolist()
            except Exception as e:
                print(f"DEBUG: Deep Learning inference failed: {e}. Falling back to simple features.")

        # FALLBACK: Simple Explainable Features (same as before)
        # Convert image back to 0–255 range
        image_uint8 = (image * 255).astype(np.uint8)

        # Convert to grayscale
        gray = cv2.cvtColor(image_uint8, cv2.COLOR_BGR2GRAY)

        # Grayscale histogram (64 bins)
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()

        # Edge features
        edges = cv2.Canny(gray, 100, 200)
        edge_mean = np.mean(edges)
        edge_std = np.std(edges)

        # Final embedding
        embedding = np.concatenate([hist, [edge_mean, edge_std]])

        return embedding.tolist()
