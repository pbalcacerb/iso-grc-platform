"""Tests de checklist y auditorías M2."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Standard
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


def test_checklist_creation_and_update(test_db: Session):
    unique_email = f"check_{uuid.uuid4().hex[:8]}@test.com"
    
    # 1. Registro y login
    client.post("/auth/register", json={"email": unique_email, "password": "pass", "full_name": "Check User"})
    client.post("/auth/login", json={"email": unique_email, "password": "pass"})

    # 2. Crear cliente
    res_client = client.post("/api/clients", json={"name": "Check Client", "sector": "Tech", "country": "US", "confidentiality_level": "medium"})
    assert res_client.status_code == 200, f"Failed to create client: {res_client.json()}"
    client_id = res_client.json()["id"]

    # 3. Obtener standard_id del seed
    std = test_db.query(Standard).filter(Standard.code == "ISO9001-DEMO").first()
    assert std is not None, "Standard ISO9001-DEMO no encontrado."
    standard_id = str(std.id)

    # 4. Crear auditoría
    res_audit = client.post("/api/audits", json={
        "client_id": client_id,
        "standard_id": standard_id,
        "name": "Test Audit",
        "status": "planned"
    })
    assert res_audit.status_code == 200, f"Failed to create audit: {res_audit.json()}"
    audit_id = res_audit.json()["id"]

    # 5. Obtener checklist
    res_checklist = client.get(f"/api/audits/{audit_id}/checklist")
    assert res_checklist.status_code == 200
    checklist = res_checklist.json()
    assert len(checklist) > 0, "El checklist debería tener items generados"

    # 6. Actualizar un item
    item_id = checklist[0]["id"]
    res_update = client.post(f"/api/audits/{audit_id}/checklist/{item_id}", json={
        "response": "Yes, we have this.",
        "notes": "Verified by manager.",
        "status": "completed"
    })
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "completed"