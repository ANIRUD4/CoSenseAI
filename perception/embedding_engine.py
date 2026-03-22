"""
perception/embedding_engine.py

Three-tier embedding engine:
  Tier 1 (MobileCLIP-S1)    – ultra-lightweight CLIP variant optimised for edge
                               CPUs.  512-d L2-normalised output.  3× faster than
                               ViT-B/32 at comparable accuracy.
  Tier 2 (TFLite MobileNet) – existing quantised model if MobileCLIP unavailable.
  Tier 3 (Simple CV)        – histogram + edge features; last resort.
"""

import cv2
import numpy as np
import os
import platform

try:
    import torch
    import open_clip
except ImportError:
    pass

# ---------- CLIP embedding dimension (MobileCLIP-S1 / ViT-B/32) ----------
# Both models output 512-d vectors in their default configuration.
CLIP_EMBEDDING_DIM = 512

# Model config for preferred edge CLIP variant.
# MobileCLIP-S1: smallest/fastest of the MobileCLIP family, still strong accuracy.
# Fallback: ViT-B-32 / openai (heavier but universally available).
_MOBILE_CLIP_MODEL  = "MobileCLIP-S1"
_MOBILE_CLIP_PRETRAINED = "datacompdr"
_FALLBACK_CLIP_MODEL = "ViT-B-32"
_FALLBACK_CLIP_PRETRAINED = "openai"

class EmbeddingEngine:
    """
    Extracts semantic visual embeddings.

    Primary:  OpenCLIP ViT-B/32  → 512-d L2-normalised vector
    Fallback: TFLite MobileNetV3 → variable-dim vector
    Last:     Simple CV features → 66-d vector
    """

    def __init__(self, model_path: str = "models/mobilenet_v3_small_quant.tflite", engine_preference: str = None):
        """
        engine_preference: 'clip', 'tflite', or 'simple'. If provided, it will try that engine first.
        """
        self.model_path = model_path
        self._engine_preference = engine_preference
        self._active_engine = "simple"
        self._clip_model_name = None  # track which CLIP model loaded

        # ── Tier 1: CLIP / OpenCLIP ────────────────────────────────────────
        self._clip_model   = None
        self._clip_preprocess = None
        self._clip_device  = "cpu"

        try:
            if self._engine_preference is None or self._engine_preference == "clip":
                # ── Attempt 1: MobileCLIP-S1 (preferred, edge-optimised) ────────────
                loaded = False
                try:
                    model, _, preprocess = open_clip.create_model_and_transforms(
                        _MOBILE_CLIP_MODEL, pretrained=_MOBILE_CLIP_PRETRAINED
                    )
                    model.eval()
                    self._clip_model         = model
                    self._clip_preprocess    = preprocess
                    self._clip_device        = "cuda" if torch.cuda.is_available() else "cpu"
                    self._clip_model.to(self._clip_device)
                    self._active_engine      = "clip"
                    self._clip_model_name    = _MOBILE_CLIP_MODEL
                    loaded = True
                    print(
                        f"INFO: MobileCLIP-S1 embedding engine loaded ({CLIP_EMBEDDING_DIM}-d) "
                        f"on {self._clip_device}"
                    )
                except Exception as e_mobile:
                    print(f"INFO: MobileCLIP-S1 unavailable ({e_mobile}). Trying ViT-B/32 fallback.")

                # ── Attempt 2: ViT-B/32 (heavier but universal CLIP fallback) ───
                if not loaded:
                    try:
                        model, _, preprocess = open_clip.create_model_and_transforms(
                            _FALLBACK_CLIP_MODEL, pretrained=_FALLBACK_CLIP_PRETRAINED
                        )
                        model.eval()
                        self._clip_model         = model
                        self._clip_preprocess    = preprocess
                        self._clip_device        = "cuda" if torch.cuda.is_available() else "cpu"
                        self._clip_model.to(self._clip_device)
                        self._active_engine      = "clip"
                        self._clip_model_name    = _FALLBACK_CLIP_MODEL
                        print(
                            f"INFO: ViT-B/32 CLIP embedding engine loaded ({CLIP_EMBEDDING_DIM}-d) "
                            f"on {self._clip_device}"
                        )
                    except Exception as e_vit:
                        print(f"INFO: ViT-B/32 also unavailable ({e_vit}).")
            else:
                print(f"INFO: CLIP skipped due to engine_preference={self._engine_preference}")
        except Exception as e:
            print(f"INFO: CLIP not available ({e}). Trying TFLite fallback.")

        # ── Tier 2: TFLite MobileNet ───────────────────────────────────────
        self._interpreter   = None
        self._input_details = None
        self._output_details = None

        if self._active_engine != "clip":
            tflite = None
            is_windows = platform.system() == "Windows"

            try:
                import tflite_runtime.interpreter as _tflite
                tflite = _tflite
            except Exception:
                if not is_windows:
                    try:
                        import tensorflow.lite as _tflite
                        tflite = _tflite
                    except Exception:
                        tflite = None

            if tflite is not None and os.path.exists(self.model_path):
                try:
                    # Pi 5 Optimization: Use 4 threads for faster inference
                    self._interpreter = tflite.Interpreter(
                        model_path=self.model_path,
                        num_threads=4
                    )
                    self._interpreter.allocate_tensors()
                    self._input_details  = self._interpreter.get_input_details()
                    self._output_details = self._interpreter.get_output_details()
                    self._active_engine  = "tflite"
                    print(f"INFO: TFLite embedding engine loaded from {self.model_path}")
                except Exception as e:
                    print(f"WARNING: TFLite init failed: {e}. Using simple CV features.")
            else:
                if tflite is None:
                    print("INFO: TFLite not installed. Using simple CV features.")
                elif not os.path.exists(self.model_path):
                    print(
                        f"INFO: Model not found at {self.model_path}. Using simple CV features."
                    )

        if self._active_engine == "simple":
            print(
                "INFO: Embedding engine running in SIMPLE CV mode "
                "(histogram + edges, 66-d). Accuracy will be limited."
            )

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def embedding_dim(self) -> int:
        """Return the output dimensionality of the active engine."""
        if self._active_engine == "clip":
            return CLIP_EMBEDDING_DIM
        # TFLite dim depends on model; we don't know it statically → return 0
        # Simple CV: 64 (hist) + 2 (edge stats) = 66
        return 0 if self._active_engine == "tflite" else 66

    @property
    def active_engine(self) -> str:
        """String identifier for the active tier: 'clip', 'tflite', or 'simple'."""
        return self._active_engine

    def get_embedding(self, image: np.ndarray, normalize: bool = True) -> dict:
        """
        Convert a preprocessed image (224×224×3, float32 in [0,1]) to
        a fixed-length embedding vector.

        Returns
        -------
        dict:
            "vector": list[float]
            "engine": str
            "dim":    int
        """
        vec = self._get_raw_embedding(image)
        if normalize:
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            vec = arr.tolist()
        
        return {
            "vector": vec,
            "engine": self._active_engine,
            "dim":    len(vec)
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_raw_embedding(self, image: np.ndarray) -> list:
        # Tier 1: CLIP
        if self._active_engine == "clip":
            try:
                return self._clip_embed(image)
            except Exception as e:
                print(f"WARNING: CLIP inference failed: {e}. Falling back to TFLite.")

        # Tier 2: TFLite
        if self._interpreter is not None:
            try:
                return self._tflite_embed(image)
            except Exception as e:
                print(f"WARNING: TFLite inference failed: {e}. Falling back to simple CV.")

        # Tier 3: Simple CV
        return self._simple_embed(image)

    def _clip_embed(self, image: np.ndarray) -> list:
        """Run CLIP ViT-B/32 image encoder on a preprocessed frame."""
        import torch
        from PIL import Image

        # Convert float32 [0,1] BGR numpy array → PIL RGB Image
        image_uint8 = (image * 255).clip(0, 255).astype(np.uint8)
        image_rgb   = cv2.cvtColor(image_uint8, cv2.COLOR_BGR2RGB)
        pil_image   = Image.fromarray(image_rgb)

        # Apply CLIP's own preprocessing (resize, normalise, etc.)
        tensor = self._clip_preprocess(pil_image).unsqueeze(0).to(self._clip_device)

        with torch.no_grad():
            features = self._clip_model.encode_image(tensor)
            # L2-normalise inside CLIP space
            features = features / features.norm(dim=-1, keepdim=True)

        return features.squeeze(0).cpu().float().tolist()

    def _tflite_embed(self, image: np.ndarray) -> list:
        """Run TFLite MobileNet on a preprocessed frame."""
        input_data = np.expand_dims(image, axis=0).astype(np.float32)
        self._interpreter.set_tensor(self._input_details[0]["index"], input_data)
        self._interpreter.invoke()
        embedding = self._interpreter.get_tensor(self._output_details[0]["index"])
        return embedding.flatten().tolist()

    def _simple_embed(self, image: np.ndarray) -> list:
        """Fallback: grayscale histogram + edge statistics (66-d)."""
        image_uint8 = (image * 255).clip(0, 255).astype(np.uint8)
        gray = cv2.cvtColor(image_uint8, cv2.COLOR_BGR2GRAY)

        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()

        edges     = cv2.Canny(gray, 100, 200)
        edge_mean = float(np.mean(edges))
        edge_std  = float(np.std(edges))

        return np.concatenate([hist, [edge_mean, edge_std]]).tolist()
