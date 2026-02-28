# learning/knowledge_unit.py

from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class KnowledgeUnit:
    embedding: List[float]
    label: str
    confidence: float
    timestamp: str

    @staticmethod
    def create(embedding, label, confidence):
        return KnowledgeUnit(
            embedding=embedding,
            label=label,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat()
        )
