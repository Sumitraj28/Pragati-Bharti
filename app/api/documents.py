from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
import os
from fastapi.responses import FileResponse
from app.db.models import Document, DocumentStatus, DocumentRole, User, Question, Answer, QuestionStatus, Page
from app.api.deps import get_current_user
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentDetailResponse,
    DocumentReviewItemsResponse,
    PageResponse,
)
from app.schemas.question import QuestionResponse
from app.services.document_service import validate_file_content, MAX_FILE_SIZE
from app.storage.local_storage import save_file
from app.workers.tasks import process_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentDetailResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all documents owned by the current authenticated user.
    """
    docs = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        DocumentDetailResponse(
            id=d.id,
            status=d.status.value,
            filename=d.filename,
            doc_role=d.doc_role.value,
            created_at=d.created_at,
        )
        for d in docs
    ]


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


@router.get("/{document_id}/questions", response_model=List[QuestionResponse])
def get_document_questions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all extracted questions for a given document.
    Must return 404 if the document does not exist or does not belong to the user.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    questions = (
        db.query(Question)
        .filter(Question.document_id == document_id)
        .order_by(Question.question_number.asc().nulls_last(), Question.id.asc())
        .all()
    )
    return questions


@router.get("/{document_id}/review-items", response_model=DocumentReviewItemsResponse)
def get_document_review_items(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all review items for a document:
    - Questions with status='needs_review'
    - Unmatched answers (for this document or its document group)
    Must return 404 if document does not exist or does not belong to the user.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 1. Questions with status='needs_review'
    needs_review_questions = (
        db.query(Question)
        .filter(Question.document_id == document_id, Question.status == QuestionStatus.NEEDS_REVIEW)
        .order_by(Question.question_number.asc().nulls_last(), Question.id.asc())
        .all()
    )

    # 2. Unmatched answers:
    # Look for answers where source_document_id == document_id,
    # or if document belongs to a group, any unmatched answers from documents in that group
    doc_ids_to_check = [document_id]
    if doc.group_id:
        sibling_ids = (
            db.query(Document.id)
            .filter(Document.group_id == doc.group_id)
            .all()
        )
        doc_ids_to_check = [sid[0] for sid in sibling_ids]

    unmatched_answers = (
        db.query(Answer)
        .filter(Answer.source_document_id.in_(doc_ids_to_check), Answer.matched == False)
        .order_by(Answer.id.asc())
        .all()
    )

    return DocumentReviewItemsResponse(
        document_id=doc.id,
        needs_review_questions=needs_review_questions,
        unmatched_answers=unmatched_answers,
    )


@router.get("/{document_id}/pages", response_model=List[PageResponse])
def get_document_pages(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all extracted pages for a document with page numbers, text, and image URLs.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    pages = (
        db.query(Page)
        .filter(Page.document_id == document_id)
        .order_by(Page.page_number.asc())
        .all()
    )
    return [
        PageResponse(
            id=p.id,
            document_id=p.document_id,
            page_number=p.page_number,
            raw_text=p.raw_text,
            image_url=f"/documents/{document_id}/pages/{p.page_number}/image" if p.image_path else None,
        )
        for p in pages
    ]


@router.get("/{document_id}/pages/{page_number}/image")
def get_page_image(
    document_id: int,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the rendered PNG image of the requested document page.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    page = (
        db.query(Page)
        .filter(Page.document_id == document_id, Page.page_number == page_number)
        .first()
    )
    if not page or not page.image_path or not os.path.exists(page.image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page image not found",
        )

    return FileResponse(page.image_path, media_type="image/png")

