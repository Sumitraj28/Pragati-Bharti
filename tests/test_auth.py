import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_success():
    """Test successful user registration."""
    email = f"register_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "SuperSecretPassword123!"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email_fails():
    """Test that registering with an already existing email returns 400."""
    email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "FirstPassword123!"
    }
    # Initial registration
    first_res = client.post("/auth/register", json=payload)
    assert first_res.status_code == 201

    # Duplicate attempt
    second_res = client.post("/auth/register", json=payload)
    assert second_res.status_code == 400
    assert second_res.json()["detail"] == "Email already registered"


def test_login_success():
    """Test successful login returns JWT access token."""
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"
    # Register user first
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201

    # Attempt login
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_wrong_password_fails():
    """Test login with incorrect password returns 401."""
    email = f"wrong_pwd_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201

    # Login with wrong password
    login_res = client.post("/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Incorrect email or password"


def test_protected_route_without_token_fails_401():
    """Test accessing a protected route without a token fails with 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_protected_route_with_valid_token_succeeds():
    """Test accessing a protected route with valid Bearer token succeeds."""
    email = f"protected_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"
    reg_res = client.post("/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201

    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Access protected route
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
