from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, DocumentStatus, DocumentRole, User
from app.api.deps import get_current_user
from app.schemas.document import DocumentUploadResponse, DocumentDetailResponse
from app.services.document_service import validate_file_content, MAX_FILE_SIZE
from app.storage.local_storage import save_file
from app.workers.tasks import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accepts multipart file upload (PDF, JPG, JPEG, PNG).
    Validates file size (20MB limit) and magic bytes.
    Stores file securely using UUID-based path.
    Inserts Document row with status=pending.
    """
    # Read file with size check
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 20MB limit.",
        )

    # Validate file extension and magic byte signature
    content_type = validate_file_content(file.filename or "", content)

    # Save to storage (UUID-based filename)
    storage_path = save_file(content, file.filename or "")

    # Insert Document row
    document = Document(
        owner_id=current_user.id,
        filename=file.filename or "unknown",
        file_type=content_type,
        storage_path=storage_path,
        status=DocumentStatus.PENDING,
        doc_role=DocumentRole.UNKNOWN,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Enqueue background processing task via Celery
    process_document.delay(document.id)

    return DocumentUploadResponse(
        id=document.id,
        status=document.status.value,
        filename=document.filename,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns document details: status, filename, doc_role, created_at.
    Must return 404 if the document does not exist or does not belong to the requesting user.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentDetailResponse(
        id=doc.id,
        status=doc.status.value,
        filename=doc.filename,
        doc_role=doc.doc_role.value,
        created_at=doc.created_at,
    )
