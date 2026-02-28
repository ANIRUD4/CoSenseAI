from fastapi import APIRouter, HTTPException

from backend.action.registry import get_action


router = APIRouter(prefix="/act", tags=["Action"])


@router.post("/")
def perform_action(req: dict):

    label = req.get("label")
    intent = req.get("intent")

    if not label or not intent:
        raise HTTPException(400, "label and intent required")

    action_fn = get_action(label, intent)

    if not action_fn:
        raise HTTPException(
            404,
            f"No action for {label} + {intent}"
        )

    result = action_fn(label)

    return {
        "status": "executed",
        "label": label,
        "intent": intent,
        "result": result
    }
