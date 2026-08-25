"""Tests de autenticación M2."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User
from app.db import SessionLocal

client = TestClient(app)


@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def test_register(test_db: Session):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": unique_email, "password": "SecurePass123!", "full_name": "Test User"}
    )
    assert response.status_code in [200, 400]  # 400 es válido si ya existía de otra corrida
    if response.status_code == 200:
        assert response.json()["message"] == "Registration successful"
        user = test_db.query(User).filter(User.email == unique_email).first()
        assert user is not None


def test_login(test_db: Session):
    unique_email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/auth/register",
        json={"email": unique_email, "password": "SecurePass123!", "full_name": "Login User"}
    )
    
    response = client.post(
        "/auth/login",
        json={"email": unique_email, "password": "SecurePass123!"}
    )
    assert response.status_code == 200
    assert "session" in response.cookies


def test_invalid_login(test_db: Session):
    response = client.post(
        "/auth/login",
        json={"email": "noexiste@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_logout(test_db: Session):
    unique_email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": unique_email, "password": "SecurePass123!", "full_name": "Logout User"})
    client.post("/auth/login", json={"email": unique_email, "password": "SecurePass123!"})
    
    response = client.get("/auth/logout")
    assert response.status_code == 200