"""
learning/tflite_classifier.py

Optional TFLite Fine-Tuned Classifier
======================================
Loads `models/objects.tflite` (a TFLite Model-Maker export) when present and
runs inference for classes that have enough training data (≥ MIN_SAMPLES_FOR_TFLITE).

Integration with infer.py
--------------------------
- If `objects.tflite` is absent or TFLite is unavailable → predict() returns None
  and the prototype similarity path takes over silently.
- If TFLite confidence ≥ TFLITE_CONFIDENCE_THRESHOLD → use its label.
- Otherwise → fall back to CLIP prototype similarity result.

Training workflow (off-device, recommended on a laptop/PC)
-----------------------------------------------------------
1. Export captured images to data/<label>/*.jpg
2. Run TFLite Model Maker:
       python scripts/train_tflite.py   (see scripts/ directory)
3. Copy objects.tflite to the Pi:
       scp models/objects.tflite pi@raspberrypi:~/IntelShareAI/models/
4. Restart the backend — the new model is loaded automatically.
"""

import os
import platform
import numpy as np

# Path to the fine-tuned TFLite model.
TFLITE_MODEL_PATH: str = "models/objects.tflite"

# Only use TFLite classifier when this many prototypes exist for a class.
# Below this count, CLIP prototypes are more reliable.
MIN_SAMPLES_FOR_TFLITE: int = 20

# Minimum TFLite confidence to override the prototype similarity result.
TFLITE_CONFIDENCE_THRESHOLD: float = 0.65


class TFLiteClassifier:
    """
    Wraps a fine-tuned TFLite image classifier.

    Usage
    -----
    clf = TFLiteClassifier()           # loads model if available
    result = clf.predict(image, label_map)
    # result → {"label": "red_mug", "confidence": 0.82} or None
    """

    def __init__(self, model_path: str = TFLITE_MODEL_PATH):
        self.model_path = model_path
        self._interpreter    = None
        self._input_details  = None
        self._output_details = None
        self._available      = False

        self._load()

    # ── Initialisation ─────────────────────────────────────────────────────

    def _load(self):
        if not os.path.exists(self.model_path):
            print(
                f"INFO: TFLiteClassifier — model not found at '{self.model_path}'. "
                "Prototype similarity will be used for all classes."
            )
            return

        tflite = self._import_tflite()
        if tflite is None:
            print(
                "INFO: TFLiteClassifier — TFLite runtime unavailable. "
                "Prototype similarity will be used for all classes."
            )
            return

        try:
            self._interpreter = tflite.Interpreter(model_path=self.model_path)
            self._interpreter.allocate_tensors()
            self._input_details  = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()
            self._available = True
            print(f"INFO: TFLiteClassifier loaded from '{self.model_path}'")
        except Exception as e:
            print(f"WARNING: TFLiteClassifier init failed: {e}")

    @staticmethod
    def _import_tflite():
        """Import tflite_runtime or tensorflow.lite, whichever is available."""
        try:
            import tflite_runtime.interpreter as tflite
            return tflite
        except ImportError:
            pass

        if platform.system() != "Windows":
            try:
                import tensorflow.lite as tflite
                return tflite
            except Exception:
                pass

        return None

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._available

    def predict(
        self,
        image: np.ndarray,
        label_map: dict,
    ) -> dict | None:
        """
        Run inference on a preprocessed image (224×224×3 float32 [0,1]).

        Parameters
        ----------
        image     : preprocessed frame (same as passed to EmbeddingEngine)
        label_map : dict mapping TFLite output index (int) to label (str).
                    This must match the class order used during Model Maker training.
                    Example: {0: "red_mug", 1: "blue_bottle"}

        Returns
        -------
        dict {"label": str, "confidence": float}  — if TFLite is available and
                                                     confidence ≥ threshold.
        None                                       — if TFLite unavailable or
                                                     confidence below threshold.
        """
        if not self._available or not label_map:
            return None

        try:
            input_data = np.expand_dims(image, axis=0).astype(np.float32)
            self._interpreter.set_tensor(
                self._input_details[0]["index"], input_data
            )
            self._interpreter.invoke()

            probs = self._interpreter.get_tensor(
                self._output_details[0]["index"]
            )[0]

            best_idx  = int(np.argmax(probs))
            best_conf = float(probs[best_idx])
            best_lbl  = label_map.get(best_idx, f"class_{best_idx}")

            print(
                f"TFLite classifier: label='{best_lbl}' "
                f"confidence={best_conf:.3f}"
            )

            if best_conf >= TFLITE_CONFIDENCE_THRESHOLD:
                return {"label": best_lbl, "confidence": best_conf}

            print(
                f"TFLite confidence {best_conf:.3f} < threshold "
                f"{TFLITE_CONFIDENCE_THRESHOLD} → falling back to prototype similarity."
            )
            return None

        except Exception as e:
            print(f"WARNING: TFLiteClassifier.predict() failed: {e}")
            return None


# ── Singleton ───────────────────────────────────────────────────────────────

_CLASSIFIER: TFLiteClassifier | None = None


def get_classifier() -> TFLiteClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = TFLiteClassifier()
    return _CLASSIFIER


# ── Quick self-test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    clf = TFLiteClassifier()
    print(f"TFLiteClassifier available: {clf.available}")
    if not clf.available:
        result = clf.predict(np.zeros((224, 224, 3), dtype=np.float32), {0: "test"})
        assert result is None, "Expected None when model is absent"
        print("PASS: predict() correctly returns None when model is absent.")
