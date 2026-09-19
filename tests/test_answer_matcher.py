import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.models import (
    Answer,
    Document,
    DocumentGroup,
    DocumentRole,
    DocumentStatus,
    Page,
    Question,
    QuestionStatus,
    User,
)
from app.services.answer_matcher import (
    detect_answer_key_content,
    find_best_question_match,
    parse_answers_rule_based,
    match_and_store_answers,
)
from app.services.security import get_password_hash, create_access_token

from app.db.session import SessionLocal

client = TestClient(app)


def test_detect_answer_key_content():
    assert detect_answer_key_content("Answer Key\n1. A\n2. B") is True
    assert detect_answer_key_content("Answers:\n1: Paris\n2: Rome") is True
    assert detect_answer_key_content("Solutions & Explanations\nQ1. (C)") is True
    assert detect_answer_key_content("Q1. (A)\nQ2. (B)\nQ3. (C)") is True
    assert detect_answer_key_content("Just some normal reading text about biology.") is False


def test_parse_answers_rule_based():
    text = """Answer Key
1. (B) Paris
Q2: 100°C
Question 3 -> Option D
99. Photosynthesis produces glucose
- Ambiguous line without number
"""
    parsed = parse_answers_rule_based(text)
    assert len(parsed) >= 4
    p1 = next((p for p in parsed if p["question_number"] == 1), None)
    assert p1 is not None
    assert "(B) Paris" in p1["raw_answer_text"]

    p2 = next((p for p in parsed if p["question_number"] == 2), None)
    assert p2 is not None
    assert "100°C" in p2["raw_answer_text"]

    p99 = next((p for p in parsed if p["question_number"] == 99), None)
    assert p99 is not None
    assert "Photosynthesis" in p99["raw_answer_text"]


def test_find_best_question_match():
    q1 = Question(
        id=101,
        document_id=1,
        question_number=1,
        question_text="What is the capital of France?",
        options=["(A) Berlin", "(B) Paris", "(C) Madrid"],
        status=QuestionStatus.EXTRACTED,
    )
    q2 = Question(
        id=102,
        document_id=1,
        question_number=2,
        question_text="What is the boiling point of water?",
        options=["(A) 50°C", "(B) 100°C"],
        status=QuestionStatus.EXTRACTED,
    )
    questions = [q1, q2]

    # 1. Exact match by question_number
    item1 = {"question_number": 1, "raw_answer_text": "(B) Paris", "ambiguous": False}
    matched_q, conf, reason = find_best_question_match(item1, questions)
    assert matched_q is not None
    assert matched_q.id == 101
    assert conf == 1.0
    assert reason is None

    # 2. Match by text similarity without question_number
    item2 = {"question_number": None, "raw_answer_text": "boiling point of water", "ambiguous": True}
    matched_q, conf, reason = find_best_question_match(item2, questions)
    assert matched_q is not None
    assert matched_q.id == 102
    assert conf >= 0.70

    # 3. Deliberately unmatched item (question_number 99 does not exist, low similarity)
    item99 = {"question_number": 99, "raw_answer_text": "Photosynthesis produces glucose", "ambiguous": False}
    matched_q, conf, reason = find_best_question_match(item99, questions)
    assert matched_q is None
    assert reason is not None
    assert "99 not found" in reason


def test_answer_matcher_fixed_pair_unit_test():
    """Unit test answer matcher with fixed question/answer pairs."""
    fixed_question = Question(
        id=42,
        document_id=1,
        question_number=5,
        question_text="What is the unit of electric charge?",
        options=["(A) Coulomb", "(B) Ampere", "(C) Volt", "(D) Ohm"],
        status=QuestionStatus.EXTRACTED,
    )
    questions = [fixed_question]

    # Test 1: Fixed pair with exact question number
    ans1 = {"question_number": 5, "raw_answer_text": "(A) Coulomb", "ambiguous": False}
    matched_q, conf, reason = find_best_question_match(ans1, questions)
    assert matched_q is not None
    assert matched_q.id == 42
    assert conf == 1.0
    assert reason is None

    # Test 2: Fixed pair with text similarity fallback (no number provided)
    ans2 = {"question_number": None, "raw_answer_text": "Coulomb", "ambiguous": True}
    matched_q, conf, reason = find_best_question_match(ans2, questions)
    assert matched_q is not None
    assert matched_q.id == 42
    assert conf >= 0.70
    assert reason is None

    # Test 3: Fixed pair that does not match
    ans3 = {"question_number": None, "raw_answer_text": "Mitochondria produces ATP", "ambiguous": False}
    matched_q, conf, reason = find_best_question_match(ans3, questions)
    assert matched_q is None
    assert conf < 0.70
    assert reason is not None
    assert "below threshold" in reason


def test_document_groups_and_review_items_api():
    db = SessionLocal()
    try:
        # Setup test user
        import uuid
        email = f"groups_tester_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=email,
            hashed_password=get_password_hash("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"sub": user.email, "user_id": user.id})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Document Group
        grp_res = client.post("/document-groups", json={"name": "Midterm Exam 2026"}, headers=headers)
        assert grp_res.status_code == 201
        grp_id = grp_res.json()["id"]

        # 2. Create documents
        doc_qp = Document(
            owner_id=user.id,
            filename="exam_paper.pdf",
            file_type="application/pdf",
            storage_path="/tmp/fake_qp.pdf",
            status=DocumentStatus.DONE,
            doc_role=DocumentRole.QUESTION_PAPER,
        )
        doc_ak = Document(
            owner_id=user.id,
            filename="exam_answers.pdf",
        file_type="application/pdf",
        storage_path="/tmp/fake_ak.pdf",
        status=DocumentStatus.DONE,
        doc_role=DocumentRole.ANSWER_KEY,
    )
        db.add_all([doc_qp, doc_ak])
        db.commit()
        db.refresh(doc_qp)
        db.refresh(doc_ak)

        # 3. Add questions to doc_qp (one extracted, one needs_review)
        q1 = Question(
            document_id=doc_qp.id,
            question_number=1,
            question_text="What is the capital of France?",
            options=["(A) Berlin", "(B) Paris"],
            confidence_score=1.0,
            status=QuestionStatus.EXTRACTED,
        )
        q2 = Question(
            document_id=doc_qp.id,
            question_number=2,
            question_text="Describe the mechanism of quantum entanglement in detail",
            options=None,
            confidence_score=0.4,
            status=QuestionStatus.NEEDS_REVIEW,
        )
        db.add_all([q1, q2])
        db.commit()
        db.refresh(q1)
        db.refresh(q2)

        # 4. Link documents to group via POST /document-groups/{id}/add
        add_qp_res = client.post(f"/document-groups/{grp_id}/add", json={"document_id": doc_qp.id}, headers=headers)
        assert add_qp_res.status_code == 200
        add_ak_res = client.post(f"/document-groups/{grp_id}/add", json={"document_id": doc_ak.id}, headers=headers)
        assert add_ak_res.status_code == 200

        # 5. Insert one matched answer and one unmatched answer
        ans_matched = Answer(
            question_id=q1.id,
            raw_answer_text="(B) Paris",
            matched=True,
            confidence_score=1.0,
            source_document_id=doc_ak.id,
            unmatched_reason=None,
        )
        ans_unmatched = Answer(
            question_id=None,
            raw_answer_text="99. Photosynthesis produces glucose",
            matched=False,
            confidence_score=0.2,
            source_document_id=doc_ak.id,
            unmatched_reason="Question number 99 not found in document questions",
        )
        db.add_all([ans_matched, ans_unmatched])
        db.commit()
        db.refresh(ans_matched)
        db.refresh(ans_unmatched)

        # 6. Test GET /questions/{id}/answer
        ans_q1_res = client.get(f"/questions/{q1.id}/answer", headers=headers)
        assert ans_q1_res.status_code == 200
        assert ans_q1_res.json()["status"] == "matched"
        assert ans_q1_res.json()["answer"]["raw_answer_text"] == "(B) Paris"

        ans_q2_res = client.get(f"/questions/{q2.id}/answer", headers=headers)
        assert ans_q2_res.status_code == 200
        assert ans_q2_res.json()["status"] == "unmatched"
        assert "No confident answer match found" in ans_q2_res.json()["reason"]

        # 7. Test GET /documents/{id}/review-items
        rev_res = client.get(f"/documents/{doc_qp.id}/review-items", headers=headers)
        assert rev_res.status_code == 200
        data = rev_res.json()
        assert data["document_id"] == doc_qp.id
        assert len(data["needs_review_questions"]) == 1
        assert data["needs_review_questions"][0]["id"] == q2.id
        assert len(data["unmatched_answers"]) == 1
        assert data["unmatched_answers"][0]["matched"] is False
        assert "Question number 99" in data["unmatched_answers"][0]["unmatched_reason"]

        # 8. Test authorization isolation: other user cannot access review items
        other_user = User(
            email=f"unauthorized_review_{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=get_password_hash("Password123!"),
        )
        db.add(other_user)
        db.commit()
        other_token = create_access_token(data={"sub": other_user.email, "user_id": other_user.id})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        rev_unauth = client.get(f"/documents/{doc_qp.id}/review-items", headers=other_headers)
        assert rev_unauth.status_code == 404
    finally:
        db.close()
