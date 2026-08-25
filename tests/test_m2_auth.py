import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session_with_rls
from app.main import app
from app.models import Membership, Tenant, User

client = TestClient(app)

@pytest.fixture
def test_db():
    # Setup test database
    db = get_session_with_rls(None, None)
    yield db
    db.rollback()


def test_register(test_db: Session):
    # Test registration
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password", "full_name": "Test User"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Registration successful"

    # Verify user, tenant, and membership were created
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    tenant = test_db.query(Tenant).filter(Tenant.slug == "test").first()
    assert tenant is not None
    membership = test_db.query(Membership).filter(Membership.user_id == user.id).first()
    assert membership is not None


def test_login(test_db: Session):
    # Setup: register a user
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password", "full_name": "Test User"}
    )

    # Test login
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "session" in response.cookies


def test_invalid_login(test_db: Session):
    # Test invalid login
    response = client.post(
        "/auth/login",
        json={"email": "invalid@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_logout():
    # Test logout
    response = client.get("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logout successful"
    assert "session" not in response.cookies