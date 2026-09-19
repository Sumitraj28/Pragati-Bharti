from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Answer, Document, Question, User, QuestionStatus
from app.api.deps import get_current_user
from app.schemas.question import QuestionResponse, QuestionUpdateRequest
from app.schemas.answer import QuestionAnswerResponse, AnswerResponse

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


@router.get("/{question_id}/answer", response_model=QuestionAnswerResponse)
def get_question_answer(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the matched answer for the given question, or 'unmatched' with a reason.
    Must return 404 if question does not exist or does not belong to current user.
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

    # Look for matched answer
    matched_answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id, Answer.matched == True)
        .first()
    )
    if matched_answer:
        return QuestionAnswerResponse(
            status="matched",
            question_id=question.id,
            answer=AnswerResponse.model_validate(matched_answer),
            reason=None,
        )

    # Check if there was an unconfident answer attempted for this question
    unmatched_answer = (
        db.query(Answer)
        .filter(Answer.question_id == question.id, Answer.matched == False)
        .first()
    )
    reason = (
        unmatched_answer.unmatched_reason
        if unmatched_answer and unmatched_answer.unmatched_reason
        else "No confident answer match found for this question."
    )

    return QuestionAnswerResponse(
        status="unmatched",
        question_id=question.id,
        answer=None,
        reason=reason,
    )


@router.patch("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    body: QuestionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates or reviews an extracted question (e.g. approving, editing text/options, or marking status).
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

    if body.question_text is not None:
        question.question_text = body.question_text
    if body.question_number is not None:
        question.question_number = body.question_number
    if body.options is not None:
        question.options = body.options
    if body.status is not None:
        question.status = QuestionStatus(body.status)

    db.commit()
    db.refresh(question)
    return question
