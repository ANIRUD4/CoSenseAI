from pydantic import BaseModel
from typing import List
from datetime import datetime

class KnowledgeUnit(BaseModel):
    id: str
    label: str
    embedding: List[float]
    confidence: float
    explanation: str
    created_at: datetime
