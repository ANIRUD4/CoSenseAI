"""
scripts/train_tflite.py

Off-device TFLite Model Maker Training Script
==============================================
Run this on a laptop/PC (not the Raspberry Pi) once you have collected
≥ 20 images per object class.

Prerequisites
-------------
    pip install tflite-model-maker pillow

Usage
-----
    # 1. Export captured images from Pi to this machine's data/ folder:
    #       scp -r pi@raspberrypi:~/IntelShareAI/data/ ./data/
    #
    # 2. Verify data layout:
    #       data/
    #         red_mug/   (≥ 20 .jpg / .png images)
    #         blue_bottle/
    #         ...
    #
    # 3. Run training:
    #       python scripts/train_tflite.py
    #
    # 4. Copy output model to the Pi:
    #       scp models/objects.tflite pi@raspberrypi:~/IntelShareAI/models/
    #
    # 5. Restart the IntelShareAI backend on the Pi — it auto-loads the model.

Output
------
    models/objects.tflite   — quantised, optimised for Raspberry Pi
    models/label_map.json   — {index: label} mapping used by TFLiteClassifier
"""

import os
import json


DATA_DIR        = "data"
OUTPUT_DIR      = "models"
OUTPUT_MODEL    = os.path.join(OUTPUT_DIR, "objects.tflite")
OUTPUT_LABELMAP = os.path.join(OUTPUT_DIR, "label_map.json")

# Minimum images per class to include in training.
MIN_IMAGES_PER_CLASS = 10


def check_data_dir():
    classes = [
        d for d in sorted(os.listdir(DATA_DIR))
        if os.path.isdir(os.path.join(DATA_DIR, d))
        and not d.startswith(".")
    ]

    valid = []
    for cls in classes:
        imgs = [
            f for f in os.listdir(os.path.join(DATA_DIR, cls))
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if len(imgs) >= MIN_IMAGES_PER_CLASS:
            valid.append((cls, len(imgs)))
            print(f"  ✓ {cls}: {len(imgs)} images")
        else:
            print(f"  ✗ {cls}: only {len(imgs)} images (need {MIN_IMAGES_PER_CLASS}+, skipped)")

    return [c for c, _ in valid]


def train(classes):
    try:
        import tflite_model_maker
        from tflite_model_maker import image_classifier
        from tflite_model_maker.image_classifier import DataLoader
        import tensorflow as tf
    except ImportError:
        print(
            "\nERROR: tflite-model-maker not installed.\n"
            "Install it with:  pip install tflite-model-maker\n"
            "Note: Requires Python 3.8–3.10 and TensorFlow 2.x"
        )
        raise

    print(f"\nLoading dataset from '{DATA_DIR}' …")
    data = DataLoader.from_folder(DATA_DIR)
    train_data, rest    = data.split(0.8)
    val_data, test_data = rest.split(0.5)

    print("Training EfficientNet-Lite0 image classifier …")
    model = image_classifier.create(
        train_data,
        validation_data=val_data,
        epochs=10,
    )

    print("\nEvaluating on test set:")
    loss, accuracy = model.evaluate(test_data)
    print(f"  Loss={loss:.4f}  Accuracy={accuracy:.4f}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    model.export(export_dir=OUTPUT_DIR, tflite_filename="objects.tflite")
    print(f"\nModel saved to {OUTPUT_MODEL}")

    # Save label map
    label_map = {i: cls for i, cls in enumerate(classes)}
    with open(OUTPUT_LABELMAP, "w") as f:
        json.dump(label_map, f, indent=2)
    print(f"Label map saved to {OUTPUT_LABELMAP}")
    print(f"\nLabel map: {label_map}")


if __name__ == "__main__":
    print("=== IntelShareAI TFLite Training ===\n")
    print(f"Scanning '{DATA_DIR}' for class folders …")

    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: Data directory '{DATA_DIR}' not found.")
        print("Create it and add sub-folders named after each object class.")
        exit(1)

    classes = check_data_dir()

    if len(classes) < 2:
        print(
            f"\nERROR: Need at least 2 classes with ≥ {MIN_IMAGES_PER_CLASS} images each."
        )
        exit(1)

    print(f"\nTraining with {len(classes)} classes: {classes}")
    train(classes)
    print("\nDone. Copy models/objects.tflite to the Raspberry Pi and restart the backend.")
