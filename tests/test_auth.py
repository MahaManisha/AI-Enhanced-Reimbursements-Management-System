import uuid
import pytest
from app.utils.auth_utils import hash_password, verify_password, generate_jwt_token, decode_jwt_token


def test_password_hashing():
    plain = "SecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_jwt_generation_and_decoding(app):
    with app.app_context():
        token = generate_jwt_token(user_id=42, role="EMPLOYEE", email="test@example.com")
        assert token is not None
        assert isinstance(token, str)

        payload = decode_jwt_token(token)
        assert payload["user_id"] == 42
        assert payload["role"] == "EMPLOYEE"
        assert payload["email"] == "test@example.com"


def test_login_success(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "Password@123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["role"] == "ADMIN"


def test_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "WrongPassword999"
    })
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={
        "email": "nobody@company.com",
        "password": "Password@123"
    })
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_register_employee_success(client):
    unique_email = f"emp_{uuid.uuid4().hex[:8]}@company.com"
    res = client.post("/api/auth/register", json={
        "full_name": "Test Engineer",
        "email": unique_email,
        "password": "Password@123",
        "department": "Engineering",
        "role": "EMPLOYEE"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["email"] == unique_email


def test_register_duplicate_email(client):
    res = client.post("/api/auth/register", json={
        "full_name": "Duplicate User",
        "email": "admin@company.com",
        "password": "Password@123",
        "department": "Finance",
        "role": "ADMIN"
    })
    assert res.status_code == 409
    assert res.get_json()["success"] is False


def test_register_validation_short_password(client):
    res = client.post("/api/auth/register", json={
        "full_name": "Short Pass User",
        "email": f"short_{uuid.uuid4().hex[:6]}@company.com",
        "password": "123",
        "department": "HR"
    })
    assert res.status_code == 400
    assert "Password must be at least 6 characters" in res.get_json()["error"]


def test_get_current_profile(client, employee_headers):
    res = client.get("/api/auth/me", headers=employee_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "john.doe@company.com"

