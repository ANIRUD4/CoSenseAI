from pydantic import BaseModel
from typing import List
from backend.schemas.knowledge_unit import KnowledgeUnit

class ExportResponse(BaseModel):
    status: str
    count: int
    file_path: str

class ImportRequest(BaseModel):
    file_path: str

class ImportResponse(BaseModel):
    status: str
    imported_count: int
