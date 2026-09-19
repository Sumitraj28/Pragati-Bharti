from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.document import DocumentDetailResponse


class DocumentGroupCreateRequest(BaseModel):
    name: str


class DocumentGroupAddDocumentRequest(BaseModel):
    document_id: int


class DocumentGroupResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    documents: Optional[List[DocumentDetailResponse]] = None

    model_config = ConfigDict(from_attributes=True)
