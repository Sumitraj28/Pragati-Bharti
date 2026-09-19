from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.document import DocumentDetailResponse


class DocumentGroupCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the document group", examples=["2026 Midterm Science Exam"])


class DocumentGroupAddDocumentRequest(BaseModel):
    document_id: int = Field(..., description="ID of the document to link into this group", examples=[101])


class DocumentGroupResponse(BaseModel):
    id: int = Field(..., description="Unique document group ID", examples=[1])
    name: str = Field(..., description="Name of the document group", examples=["2026 Midterm Science Exam"])
    owner_id: int = Field(..., description="User ID of the group owner", examples=[1])
    created_at: datetime = Field(..., description="Timestamp of group creation", examples=["2026-09-19T10:10:00Z"])
    documents: Optional[List[DocumentDetailResponse]] = Field(
        default_factory=list,
        description="List of documents currently linked to this group",
    )

    model_config = ConfigDict(from_attributes=True)
