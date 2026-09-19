from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, DocumentGroup, User
from app.api.deps import get_current_user
from app.schemas.document_group import (
    DocumentGroupCreateRequest,
    DocumentGroupAddDocumentRequest,
    DocumentGroupResponse,
)
from app.schemas.document import DocumentDetailResponse
from app.services.answer_matcher import match_answers_for_group

from typing import List

router = APIRouter(prefix="/document-groups", tags=["Document Groups"])


@router.get("", response_model=List[DocumentGroupResponse])
def list_document_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists all document groups owned by the current user.
    """
    groups = (
        db.query(DocumentGroup)
        .filter(DocumentGroup.owner_id == current_user.id)
        .order_by(DocumentGroup.created_at.desc())
        .all()
    )
    result = []
    for grp in groups:
        docs = [
            DocumentDetailResponse(
                id=d.id,
                status=d.status.value,
                filename=d.filename,
                doc_role=d.doc_role.value,
                created_at=d.created_at,
            )
            for d in grp.documents
        ]
        result.append(
            DocumentGroupResponse(
                id=grp.id,
                name=grp.name,
                owner_id=grp.owner_id,
                created_at=grp.created_at,
                documents=docs,
            )
        )
    return result


@router.post("", response_model=DocumentGroupResponse, status_code=status.HTTP_201_CREATED)
def create_document_group(
    group_in: DocumentGroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a new DocumentGroup owned by the current user.
    """
    if not group_in.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name cannot be empty.",
        )

    group = DocumentGroup(
        owner_id=current_user.id,
        name=group_in.name.strip(),
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return DocumentGroupResponse(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=group.created_at,
        documents=[],
    )


@router.post("/{group_id}/add", response_model=DocumentGroupResponse)
def add_document_to_group(
    group_id: int,
    body: DocumentGroupAddDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adds an existing document owned by the user into the specified document group.
    Triggers cross-document answer matching across the group.
    """
    group = (
        db.query(DocumentGroup)
        .filter(DocumentGroup.id == group_id, DocumentGroup.owner_id == current_user.id)
        .first()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document group not found.",
        )

    doc = (
        db.query(Document)
        .filter(Document.id == body.document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    doc.group_id = group.id
    db.commit()
    db.refresh(doc)

    # Run answer matching across all documents in this group
    match_answers_for_group(group.id, db)

    # Reload group documents
    docs = db.query(Document).filter(Document.group_id == group.id).all()
    doc_responses = [
        DocumentDetailResponse(
            id=d.id,
            status=d.status.value,
            filename=d.filename,
            doc_role=d.doc_role.value,
            created_at=d.created_at,
        )
        for d in docs
    ]

    return DocumentGroupResponse(
        id=group.id,
        name=group.name,
        owner_id=group.owner_id,
        created_at=group.created_at,
        documents=doc_responses,
    )
