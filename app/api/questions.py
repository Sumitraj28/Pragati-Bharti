from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, Question, User
from app.api.deps import get_current_user
from app.schemas.question import QuestionResponse

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns question details by ID.
    Must return 404 if the question does not exist or does not belong to the requesting user's documents.
    """
    question = (
        db.query(Question)
        .join(Document, Question.document_id == Document.id)
        .filter(Question.id == question_id, Document.owner_id == current_user.id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    return question
