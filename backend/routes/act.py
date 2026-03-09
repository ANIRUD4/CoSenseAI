"""
backend/routes/act.py

Action execution route for IntelShare AI.
Improved to support dynamic text-based actions stored in the prototype store,
rather than the old hard-coded ACTION_REGISTRY.

The companion app allows users to map a label to a text description of an action
(e.g., "empty bottle" -> "Refill the bottle").
When confirmed during inference, the frontend calls /act/ with the label.
This route looks up the text action from the prototype store and returns it
as a plain text output, which the Raspberry Pi UI and Companion App can display.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.storage.prototype_store import load_prototypes


router = APIRouter(prefix="/act", tags=["Action"])


class ActionRequest(BaseModel):
    label: str
    intent: Optional[str] = None  # kept for backwards compat, not required


@router.post("/")
def perform_action(req: ActionRequest):
    """
    Looks up the text action associated with the given label from the prototype
    store. Returns a plain text output describing the action to perform.

    For the prototype, the action is text-only (no GPIO or physical control).
    The Raspberry Pi UI and Companion App display this text to the user.
    """
    label = req.label.strip().lower()

    if not label:
        raise HTTPException(status_code=400, detail="label is required")

    # Look up action in prototype store (dynamic text actions)
    prototypes = load_prototypes()
    label_data = prototypes.get(label)

    action_text = None

    if label_data:
        # Find the first prototype that has an action set
        for proto in label_data.get("prototypes", []):
            if proto.get("action"):
                action_text = proto["action"]
                break

    if not action_text:
        # No action mapped; return a friendly default
        action_text = f"Label '{label}' recognised — no action has been mapped yet."

    return {
        "status": "executed",
        "label": label,
        "action": action_text,
        "message": action_text,  # Alias for easy display in UI
    }


@router.get("/actions")
def list_mapped_actions():
    """
    Lists all labels that have a text action mapped, along with the action text.
    Used by the Companion App to display the current action mapping.
    """
    prototypes = load_prototypes()
    result = []

    for label, data in prototypes.items():
        action_text = None
        for proto in data.get("prototypes", []):
            if proto.get("action"):
                action_text = proto["action"]
                break
        result.append({
            "label": label,
            "action": action_text,
            "has_action": action_text is not None,
        })

    result.sort(key=lambda x: x["label"])
    return {"mappings": result, "count": len(result)}
