from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AnswerResponse(BaseModel):
    id: int = Field(..., description="Unique answer ID", examples=[1])
    question_id: Optional[int] = Field(None, description="Matched question ID (or null if unmatched)", examples=[24])
    raw_answer_text: str = Field(..., description="Raw text of the extracted answer", examples=["(B) Paris"])
    matched: bool = Field(..., description="True if confidently matched to a question, False otherwise", examples=[True])
    confidence_score: Optional[float] = Field(1.0, description="Match confidence score between 0.0 and 1.0", examples=[1.0])
    source_document_id: Optional[int] = Field(None, description="Document ID where this answer was found", examples=[102])
    unmatched_reason: Optional[str] = Field(None, description="Explanation if matched is False", examples=[None])
    created_at: datetime = Field(..., description="Timestamp of answer parsing/matching", examples=["2026-09-19T10:16:00Z"])

    model_config = ConfigDict(from_attributes=True)


class QuestionAnswerResponse(BaseModel):
    status: str = Field(..., description="Match status ('matched' or 'unmatched')", examples=["matched"])
    question_id: int = Field(..., description="Question ID being queried", examples=[24])
    answer: Optional[AnswerResponse] = Field(None, description="Matched Answer object if status is 'matched'")
    reason: Optional[str] = Field(None, description="Reason if status is 'unmatched'", examples=[None])
