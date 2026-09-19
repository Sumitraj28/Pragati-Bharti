from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict


class QuestionResponse(BaseModel):
    id: int
    document_id: int
    question_number: Optional[int] = None
    question_text: str
    options: Optional[Any] = None
    question_type: Optional[str] = None
    source_pages: Optional[List[int]] = None
    confidence_score: Optional[float] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
