from pydantic import BaseModel
from typing import List, Optional


class LearningRequest(BaseModel):
    label: str
    action: Optional[str] = None
    explanation: Optional[str] = None

    # ✅ Support both (for compatibility)
    embedding: Optional[List[float]] = None
    embeddings: Optional[List[List[float]]] = None
    image_base64: Optional[str] = None
    roi_bbox: Optional[dict] = None  # {x, y, w, h} as percentages [0, 1]


class LearningResponse(BaseModel):
    status: str
