"""
backend/routes/admin.py

Admin utilities for demo management.
These endpoints should NOT be exposed in production.
"""

from fastapi import APIRouter
from backend.storage.prototype_store import load_prototypes, save_prototypes
from backend.utils.drift import prune_prototypes

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.delete("/clear")
def clear_all_prototypes():
    """
    Wipe the entire prototype store.
    Use this before a demo to start completely fresh.
    """
    save_prototypes({})
    return {"status": "cleared", "message": "All prototypes deleted. Ready for a fresh demo."}


@router.delete("/clear/{label}")
def clear_label(label: str):
    """
    Delete prototypes for a single label only.
    Useful when one object was taught but needs to be re-taught.
    """
    label = label.strip().lower()
    data = load_prototypes()
    if label not in data:
        return {"status": "not_found", "message": f"Label '{label}' not in store."}
    del data[label]
    save_prototypes(data)
    return {"status": "cleared", "label": label}


@router.post("/prune")
def trigger_prune():
    """
    Manually trigger the memory pruning policy.
    Normally pruning is disabled during inference to avoid deleting fresh prototypes.
    Call this explicitly to clean up stale/weak prototypes.
    """
    data = load_prototypes()
    before = sum(len(v.get("prototypes", [])) for v in data.values())
    pruned = prune_prototypes(data)
    save_prototypes(pruned)
    after = sum(len(v.get("prototypes", [])) for v in pruned.values())
    return {
        "status": "pruned",
        "before": before,
        "after": after,
        "removed": before - after,
    }


@router.get("/status")
def get_status():
    """
    Returns the number of labels and prototypes in the store.
    Use this to verify the store is in a good state before the demo.
    """
    data = load_prototypes()
    summary = {}
    for label, info in data.items():
        protos = info.get("prototypes", [])
        user_count = sum(1 for p in protos if p.get("source", "user") == "user")
        summary[label] = {
            "total_prototypes": len(protos),
            "user_prototypes": user_count,
            "has_mean_vector": info.get("mean_vector") is not None,
        }
    return {
        "labels": len(data),
        "total_prototypes": sum(v["total_prototypes"] for v in summary.values()),
        "detail": summary,
    }
