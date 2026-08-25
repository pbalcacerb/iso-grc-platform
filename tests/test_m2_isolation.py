"""Tests de aislamiento de tenants M2."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
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


def test_tenant_isolation(test_db: Session):
    email_a = f"userA_{uuid.uuid4().hex[:8]}@test.com"
    email_b = f"userB_{uuid.uuid4().hex[:8]}@test.com"

    # 1. User A se registra y hace login
    client.post("/auth/register", json={"email": email_a, "password": "pass", "full_name": "User A"})
    client.post("/auth/login", json={"email": email_a, "password": "pass"})
    
    res_a = client.post("/api/clients", json={"name": "Client A", "sector": "Tech", "country": "US", "confidentiality_level": "high"})
    assert res_a.status_code == 200, f"Failed to create client A: {res_a.json()}"
    
    # 2. User B se registra y hace login (sobreescribe la cookie del TestClient)
    client.post("/auth/register", json={"email": email_b, "password": "pass", "full_name": "User B"})
    client.post("/auth/login", json={"email": email_b, "password": "pass"})
    
    # User B lista clientes: debería estar vacío
    res_b_list = client.get("/api/clients")
    assert res_b_list.status_code == 200
    assert len(res_b_list.json()) == 0, f"User B should see 0 clients, but saw: {res_b_list.json()}"
    
    # User B crea su propio cliente
    res_b_create = client.post("/api/clients", json={"name": "Client B", "sector": "Finance", "country": "US", "confidentiality_level": "medium"})
    assert res_b_create.status_code == 200
    
    # User B lista de nuevo: solo ve a Client B
    res_b_list2 = client.get("/api/clients")
    assert res_b_list2.status_code == 200
    clients_b2 = res_b_list2.json()
    assert len(clients_b2) == 1
    assert clients_b2[0]["name"] == "Client B"