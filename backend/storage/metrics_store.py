import json
import os
import time
from typing import Dict, List, Optional

METRICS_PATH = "data/metrics.json"

def load_metrics() -> Dict:
    defaults = {
        "events": [],
        "snapshots": [],
        "total_confirmed": 0,
        "total_corrected": 0
    }
    if not os.path.exists(METRICS_PATH):
        return defaults
    
    with open(METRICS_PATH, "r") as f:
        try:
            data = json.load(f)
            # Merge with defaults to handle incomplete files
            return {**defaults, **data}
        except json.JSONDecodeError:
            return defaults

def save_metrics(data: Dict):
    os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def log_event(label: str, confirmed: bool, confidence: float):
    """Logs a single real-world confirmation/correction event."""
    data = load_metrics()
    
    event = {
        "timestamp": time.time(),
        "label": label,
        "confirmed": confirmed,
        "confidence": float(confidence)
    }
    
    data["events"].append(event)
    
    if confirmed:
        data["total_confirmed"] += 1
    else:
        data["total_corrected"] += 1
        
    # Cap events to last 1000 to keep JSON size manageable
    if len(data["events"]) > 1000:
        data["events"] = data["events"][-1000:]
        
    save_metrics(data)

def log_snapshot(accuracy: float, class_metrics: Dict):
    """Logs a full aggregate snapshot (e.g., from a benchmark run)."""
    data = load_metrics()
    
    snapshot = {
        "timestamp": time.time(),
        "accuracy": float(accuracy),
        "class_metrics": class_metrics
    }
    
    data["snapshots"].append(snapshot)
    
    # Cap snapshots to last 100
    if len(data["snapshots"]) > 100:
        data["snapshots"] = data["snapshots"][-100:]
        
    save_metrics(data)

def get_rolling_accuracy(window: int = 50) -> float:
    """Calculates accuracy over the last N events."""
    data = load_metrics()
    events = data["events"][-window:]
    
    if not events:
        return 0.0
    
    confirmed = sum(1 for e in events if e["confirmed"])
    return confirmed / len(events)
