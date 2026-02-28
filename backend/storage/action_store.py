import json
import os
from typing import Dict, Any

ACTION_MAP_PATH = os.path.join("data", "models", "action_map.json")

def load_action_map() -> Dict[str, Any]:
    if not os.path.exists(ACTION_MAP_PATH):
        return {}
    with open(ACTION_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_action_map(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ACTION_MAP_PATH), exist_ok=True)
    with open(ACTION_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_action(label: str, intent: str):
    label = label.lower().strip()
    intent = intent.lower().strip()
    data = load_action_map()
    return data.get(label, {}).get(intent)
