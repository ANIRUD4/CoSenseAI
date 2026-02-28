from pydantic import BaseModel
from typing import List

class InferRequest(BaseModel):
    embedding: List[float] | None = None
    image_base64: str | None = None


class InferenceCandidate(BaseModel):
    id: str
    label: str
    action: str | None = None
    confidence: float

class InferenceResponse(BaseModel):
    message: str
    candidates: List[InferenceCandidate]
