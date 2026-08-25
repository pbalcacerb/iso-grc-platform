import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session_with_rls
from app.main import app

client = TestClient(app)

@pytest.fixture
def test_db():
    # Setup test database
    db = get_session_with_rls(None, None)
    yield db
    db.rollback()


def test_tenant_isolation(test_db: Session):
    # Setup: register two users (tenant A and tenant B)
    client.post(
        "/auth/register",
        json={"email": "userA@example.com", "password": "password", "full_name": "User A"}
    )
    client.post(
        "/auth/register",
        json={"email": "userB@example.com", "password": "password", "full_name": "User B"}
    )

    # Login as user A and create a client
    login_response = client.post(
        "/auth/login",
        json={"email": "userA@example.com", "password": "password"}
    )
    assert login_response.status_code == 200

    # Create a client for tenant A
    client_post_response = client.post(
        "/api/clients",
        json={"name": "Client A", "sector": "Technology", "country": "US", "confidentiality_level": "high"}
    )
    assert client_post_response.status_code == 200

    # Login as user B and verify they cannot see tenant A's client
    login_response = client.post(
        "/auth/login",
        json={"email": "userB@example.com", "password": "password"}
    )
    assert login_response.status_code == 200

    # List clients for tenant B
    clients_response = client.get("/api/clients")
    assert clients_response.status_code == 200
    clients = clients_response.json()
    assert len(clients) == 0  # Tenant B should have no clients