from datetime import datetime
from typing import List, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.question import QuestionResponse
    from app.schemas.answer import AnswerResponse


class DocumentUploadResponse(BaseModel):
    id: int = Field(..., description="Uploaded document ID", examples=[101])
    status: str = Field(..., description="Initial processing status (pending)", examples=["pending"])
    filename: str = Field(..., description="Original filename of the uploaded file", examples=["exam_paper.pdf"])

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    id: int = Field(..., description="Document ID", examples=[101])
    status: str = Field(..., description="Document processing status (pending, processing, done, failed)", examples=["done"])
    filename: str = Field(..., description="Document filename", examples=["exam_paper.pdf"])
    doc_role: str = Field(..., description="Document role (question_paper, answer_key, unknown)", examples=["question_paper"])
    created_at: datetime = Field(..., description="Upload timestamp", examples=["2026-09-19T10:15:30Z"])

    model_config = ConfigDict(from_attributes=True)


class DocumentReviewItemsResponse(BaseModel):
    document_id: int = Field(..., description="Target document ID", examples=[101])
    needs_review_questions: List["QuestionResponse"] = Field(
        default_factory=list,
        description="Questions with status=needs_review requiring human attention",
    )
    unmatched_answers: List["AnswerResponse"] = Field(
        default_factory=list,
        description="Answers extracted from answer keys that could not be matched with high confidence",
    )

    model_config = ConfigDict(from_attributes=True)


# For forward reference resolution
from app.schemas.question import QuestionResponse
from app.schemas.answer import AnswerResponse

DocumentReviewItemsResponse.model_rebuild()
