"""
Maps (label, intent) → action function
"""

from backend.action.executors import (
    highlight,
    alert,
    stop_device
)


ACTION_REGISTRY = {

    # Objects
    "apple": {
        "highlight": highlight,
        "alert": alert
    },

    "bottle": {
        "highlight": highlight
    },

    "person": {
        "alert": alert,
        "stop": stop_device
    }
}


def get_action(label: str, intent: str):

    label = label.lower()
    intent = intent.lower()

    return ACTION_REGISTRY.get(label, {}).get(intent)
