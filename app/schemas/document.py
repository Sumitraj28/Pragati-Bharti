from datetime import datetime
from pydantic import BaseModel, ConfigDict


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
