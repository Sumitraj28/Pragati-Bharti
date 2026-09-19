import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import QuestionStatus
from app.services.extraction import (
    compute_confidence_score,
    extract_questions_rule_based,
)

client = TestClient(app)

VALID_PDF = b"%PDF-1.4 test pdf content stream %%EOF"


def get_auth_headers(email: str = None) -> dict:
    """Helper to register and login a user, returning Authorization headers."""
    if not email:
        email = f"extract_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_confidence_score_rules():
    """Verifies all scoring rules specified in the requirements."""
    # 1. Digital text, question_number, options, question_text all present -> 1.0, "extracted"
    q_digital = {
        "question_number": 1,
        "question_text": "What is the capital of France?",
        "options": ["(A) Paris", "(B) London"],
        "source_pages": [1],
        "ambiguous": False,
    }
    score, status = compute_confidence_score(q_digital, ocr_pages=set())
    assert score == 1.0
    assert status == QuestionStatus.EXTRACTED

    # 2. OCR text used -> 0.7, "extracted"
    q_ocr = {
        "question_number": 2,
        "question_text": "Solve for x: 2x = 10",
        "options": ["(A) 5", "(B) 10"],
        "source_pages": [1],
        "ambiguous": False,
    }
    score_ocr, status_ocr = compute_confidence_score(q_ocr, ocr_pages={1})
    assert score_ocr == 0.7
    assert status_ocr == QuestionStatus.EXTRACTED

    # 3. Options missing -> 0.7, "extracted"
    q_no_opts = {
        "question_number": 3,
        "question_text": "Explain photosynthesis in detail.",
        "options": None,
        "source_pages": [1],
        "ambiguous": False,
    }
    score_no_opts, status_no_opts = compute_confidence_score(q_no_opts, ocr_pages=set())
    assert score_no_opts == 0.7
    assert status_no_opts == QuestionStatus.EXTRACTED

    # 4. Question number missing -> 0.4, "needs_review"
    q_no_num = {
        "question_number": None,
        "question_text": "Is energy conserved in a closed system?",
        "options": ["(A) Yes", "(B) No"],
        "source_pages": [1],
        "ambiguous": False,
    }
    score_no_num, status_no_num = compute_confidence_score(q_no_num, ocr_pages=set())
    assert score_no_num == 0.4
    assert status_no_num == QuestionStatus.NEEDS_REVIEW

    # 5. Ambiguity flagged by LLM -> 0.4, "needs_review"
    q_ambiguous = {
        "question_number": 5,
        "question_text": "Incomplete question sentence...",
        "options": ["(A) 1"],
        "source_pages": [1],
        "ambiguous": True,
    }
    score_amb, status_amb = compute_confidence_score(q_ambiguous, ocr_pages=set())
    assert score_amb == 0.4
    assert status_amb == QuestionStatus.NEEDS_REVIEW


def test_rule_based_question_parsing():
    """Test deterministic rule-based question parser on multi-page text."""
    sample_text = (
        "[PAGE 1]\n"
        "Question 1: What is the unit of electric current?\n"
        "(A) Ampere  (B) Volt  (C) Ohm  (D) Watt\n\n"
        "[PAGE 2]\n"
        "Question 2: State Newton's second law of motion.\n"
    )
    questions = extract_questions_rule_based(sample_text)
    assert len(questions) == 2

    # Question 1
    assert questions[0]["question_number"] == 1
    assert "unit of electric current" in questions[0]["question_text"]
    assert questions[0]["question_type"] == "multiple_choice"
    assert len(questions[0]["options"]) == 4
    assert questions[0]["source_pages"] == [1]

    # Question 2
    assert questions[1]["question_number"] == 2
    assert "Newton's second law" in questions[1]["question_text"]
    assert questions[1]["options"] is None
    assert questions[1]["question_type"] == "subjective"
    assert questions[1]["source_pages"] == [2]


def test_document_questions_endpoints_and_isolation():
    """Test GET /documents/{id}/questions and GET /questions/{id} with auth and ownership checks."""
    headers_a = get_auth_headers("user_qa_a@example.com")
    headers_b = get_auth_headers("user_qa_b@example.com")

    # User A uploads document
    upload_res = client.post(
        "/documents",
        headers=headers_a,
        files={"file": ("physics_test.pdf", io.BytesIO(VALID_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Unauthenticated request to /documents/{id}/questions fails with 401
    unauth_res = client.get(f"/documents/{doc_id}/questions")
    assert unauth_res.status_code == 401

    # 2. User B trying to access User A's document questions receives 404
    b_doc_res = client.get(f"/documents/{doc_id}/questions", headers=headers_b)
    assert b_doc_res.status_code == 404
    assert b_doc_res.json()["detail"] == "Document not found"

    # 3. User A can access their document questions
    a_doc_res = client.get(f"/documents/{doc_id}/questions", headers=headers_a)
    assert a_doc_res.status_code == 200
    assert isinstance(a_doc_res.json(), list)

    # 4. User B trying to access a question directly by ID receives 404
    fake_q_id = 999999
    b_q_res = client.get(f"/questions/{fake_q_id}", headers=headers_b)
    assert b_q_res.status_code == 404
    assert b_q_res.json()["detail"] == "Question not found"


from unittest.mock import patch
from app.services.extraction import call_llm_with_retry


def test_call_llm_json_parsing_success():
    """Test successful parsing of valid JSON from LLM (including code fences)."""
    mock_llm_content = """```json
[
  {
    "question_number": 1,
    "question_text": "What is the speed of sound in air?",
    "options": ["(A) 343 m/s", "(B) 300,000 km/s"],
    "question_type": "multiple_choice",
    "source_pages": [1],
    "ambiguous": false
  }
]
```"""
    with patch("app.services.extraction._call_llm_api", return_value=mock_llm_content) as mock_api:
        results = call_llm_with_retry("sample prompt text")
        assert mock_api.call_count == 1
        assert len(results) == 1
        assert results[0]["question_number"] == 1
        assert "speed of sound" in results[0]["question_text"]
        assert results[0]["options"] == ["(A) 343 m/s", "(B) 300,000 km/s"]


def test_call_llm_json_retry_on_invalid_json():
    """Test that invalid JSON triggers a retry, and succeeds on the second attempt."""
    bad_json = "I am an AI assistant. Here is your question: {invalid"
    good_json = """[
  {
    "question_number": 2,
    "question_text": "Define momentum.",
    "options": null,
    "question_type": "subjective",
    "source_pages": [1],
    "ambiguous": false
  }
]"""
    with patch("app.services.extraction._call_llm_api", side_effect=[bad_json, good_json]) as mock_api:
        results = call_llm_with_retry("sample prompt text")
        assert mock_api.call_count == 2
        assert len(results) == 1
        assert results[0]["question_number"] == 2
        assert results[0]["question_text"] == "Define momentum."


def test_call_llm_fallback_to_rule_based_on_persistent_failure():
    """Test that persistent invalid JSON falls back gracefully to rule-based parsing."""
    bad_json_1 = "invalid json response 1"
    bad_json_2 = "invalid json response 2"
    prompt_with_question = "[PAGE 1]\nQuestion 1: What is kinetic energy?\n(A) Energy of motion\n(B) Stored energy"

    with patch("app.services.extraction._call_llm_api", side_effect=[bad_json_1, bad_json_2]) as mock_api:
        results = call_llm_with_retry(prompt_with_question)
        assert mock_api.call_count == 2
        assert len(results) >= 1
        assert results[0]["question_number"] == 1
        assert "kinetic energy" in results[0]["question_text"]
