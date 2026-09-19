from datetime import datetime
from typing import List, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schemas.question import QuestionResponse
    from app.schemas.answer import AnswerResponse


class DocumentUploadResponse(BaseModel):
    id: int
    status: str
    filename: str

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    id: int
    status: str
    filename: str
    doc_role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReviewItemsResponse(BaseModel):
    document_id: int
    needs_review_questions: List["QuestionResponse"]
    unmatched_answers: List["AnswerResponse"]

    model_config = ConfigDict(from_attributes=True)


# For forward reference resolution
from app.schemas.question import QuestionResponse
from app.schemas.answer import AnswerResponse

DocumentReviewItemsResponse.model_rebuild()
