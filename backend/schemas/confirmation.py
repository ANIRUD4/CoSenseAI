from pydantic import BaseModel, Field
from typing import List, Optional

class ConfirmationRequest(BaseModel):
    predicted_label: str
    confirmed: bool
    corrected_label: Optional[str] = None
    embedding: Optional[List[float]] = None
    confidence: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


class ConfirmationResponse(BaseModel):
    status: str
