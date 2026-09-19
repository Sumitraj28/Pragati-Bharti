"""Pydantic request and response schemas."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Service health status", examples=["ok"])
    service: str = Field(..., description="Name of the service", examples=["document-intelligence-service"])
    environment: str = Field(..., description="Current deployment environment", examples=["development"])


class DocumentBase(BaseModel):
    filename: str
    content_type: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    status: str
    storage_path: str
    extracted_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.schemas.document_group import (
    DocumentGroupCreateRequest,
    DocumentGroupAddDocumentRequest,
    DocumentGroupResponse,
)
from app.schemas.answer import (
    AnswerResponse,
    QuestionAnswerResponse,
)
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentReviewItemsResponse,
)
from app.schemas.question import QuestionResponse
