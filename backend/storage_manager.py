# backend/storage_manager.py
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data/knowledge_units")

DATA_DIR.mkdir(parents=True, exist_ok=True)

def save_knowledge_unit(unit: dict):
    # Convert datetime to ISO string (JSON-safe)
    for key, value in unit.items():
        if isinstance(value, datetime):
            unit[key] = value.isoformat()

    file_path = DATA_DIR / f"{unit['id']}.json"
    with open(file_path, "w") as f:
        json.dump(unit, f, indent=2)

def load_all_units():
    units = []
    for file in DATA_DIR.glob("*.json"):
        with open(file) as f:
            units.append(json.load(f))
    return units
