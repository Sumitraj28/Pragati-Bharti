from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuestionResponse(BaseModel):
    id: int = Field(..., description="Unique question ID", examples=[1])
    document_id: int = Field(..., description="Document ID this question belongs to", examples=[101])
    question_number: Optional[int] = Field(None, description="Extracted question number", examples=[1])
    question_text: str = Field(..., description="Full text of the question", examples=["What is the capital of France?"])
    options: Optional[List[str]] = Field(None, description="List of multiple-choice options (if applicable)", examples=[["(A) Berlin", "(B) Paris", "(C) Rome", "(D) Madrid"]])
    question_type: Optional[str] = Field("multiple_choice", description="Question format (multiple_choice, subjective, true_false)", examples=["multiple_choice"])
    source_pages: Optional[List[int]] = Field(None, description="Page numbers where this question was located", examples=[[1]])
    confidence_score: Optional[float] = Field(1.0, description="Extraction confidence score between 0.0 and 1.0", examples=[1.0])
    status: str = Field(..., description="Question review status (extracted, partial, needs_review)", examples=["extracted"])
    created_at: datetime = Field(..., description="Timestamp of extraction", examples=["2026-09-19T10:15:35Z"])

    model_config = ConfigDict(from_attributes=True)


class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = Field(None, description="Updated question text")
    question_number: Optional[int] = Field(None, description="Updated question number")
    options: Optional[List[str]] = Field(None, description="Updated options list")
    status: Optional[str] = Field(None, description="New question status ('extracted', 'needs_review')")
