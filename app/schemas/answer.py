from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AnswerResponse(BaseModel):
    id: int
    question_id: Optional[int] = None
    raw_answer_text: str
    matched: bool
    confidence_score: Optional[float] = None
    source_document_id: Optional[int] = None
    unmatched_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionAnswerResponse(BaseModel):
    status: str  # "matched" or "unmatched"
    question_id: int
    answer: Optional[AnswerResponse] = None
    reason: Optional[str] = None
