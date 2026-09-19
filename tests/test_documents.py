import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Dummy valid file contents matching magic bytes
VALID_PDF = b"%PDF-1.4 test pdf content stream %%EOF"
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
VALID_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"


def get_auth_headers(email: str = None) -> dict:
    """Helper to register and login a user, returning Authorization headers."""
    if not email:
        email = f"doc_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    client.post("/auth/register", json={"email": email, "password": password})
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_valid_pdf_upload_succeeds():
    """Test that a valid PDF upload succeeds and creates a pending document."""
    headers = get_auth_headers()
    files = {
        "file": ("exam_paper.pdf", io.BytesIO(VALID_PDF), "application/pdf")
    }
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["filename"] == "exam_paper.pdf"

    # Verify GET /documents/{id} returns details
    doc_id = data["id"]
    get_res = client.get(f"/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    doc_data = get_res.json()
    assert doc_data["id"] == doc_id
    assert doc_data["status"] == "pending"
    assert doc_data["filename"] == "exam_paper.pdf"
    assert doc_data["doc_role"] == "unknown"
    assert "created_at" in doc_data


def test_valid_image_uploads_succeed():
    """Test valid PNG and JPG uploads succeed."""
    headers = get_auth_headers()

    # PNG upload
    png_res = client.post(
        "/documents",
        headers=headers,
        files={"file": ("page1.png", io.BytesIO(VALID_PNG), "image/png")},
    )
    assert png_res.status_code == 201
    assert png_res.json()["status"] == "pending"

    # JPG upload
    jpg_res = client.post(
        "/documents",
        headers=headers,
        files={"file": ("page2.jpg", io.BytesIO(VALID_JPG), "image/jpeg")},
    )
    assert jpg_res.status_code == 201
    assert jpg_res.json()["status"] == "pending"


def test_oversized_file_rejected():
    """Test that files exceeding 20MB are rejected with 400 Bad Request."""
    headers = get_auth_headers()
    # 20MB + 1KB buffer
    oversized_bytes = b"%PDF-" + (b"0" * (20 * 1024 * 1024 + 1024))
    files = {
        "file": ("huge_file.pdf", io.BytesIO(oversized_bytes), "application/pdf")
    }
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 400
    assert "20MB" in response.json()["detail"]


def test_wrong_file_extension_rejected():
    """Test that unsupported file extensions (.txt, .exe) are rejected with 400."""
    headers = get_auth_headers()
    files = {
        "file": ("malicious.exe", io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00"), "application/x-msdownload")
    }
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_invalid_magic_bytes_rejected():
    """Test that a file with .pdf extension but fake text content is rejected with 400."""
    headers = get_auth_headers()
    fake_pdf = b"Plain text content disguised as a pdf document"
    files = {
        "file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")
    }
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 400
    assert "magic bytes mismatch" in response.json()["detail"]


def test_user_a_cannot_get_user_b_document():
    """Test that User A cannot retrieve User B's document and receives a 404."""
    headers_user_a = get_auth_headers("user_a@example.com")
    headers_user_b = get_auth_headers("user_b@example.com")

    # User A uploads a document
    upload_res = client.post(
        "/documents",
        headers=headers_user_a,
        files={"file": ("user_a_secret.pdf", io.BytesIO(VALID_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # User A can get their own document
    get_res_a = client.get(f"/documents/{doc_id}", headers=headers_user_a)
    assert get_res_a.status_code == 200

    # User B attempts to access User A's document -> must return 404
    get_res_b = client.get(f"/documents/{doc_id}", headers=headers_user_b)
    assert get_res_b.status_code == 404
    assert get_res_b.json()["detail"] == "Document not found"
