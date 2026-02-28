

import os
import joblib

MODEL_DIR = "data/models"
MODEL_PATH = os.path.join(MODEL_DIR, "incremental_model.joblib")


def save_model(model):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)


def load_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None
