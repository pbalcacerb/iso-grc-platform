"""Integration tests for M3 Evidence functionality."""
import os
import uuid
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Standard

data_dir = "data/evidence"
os.makedirs(data_dir, exist_ok=True)


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as test_client:
        yield test_client
        # Limpieza post-test: eliminar archivos subidos
        for file in Path(data_dir).glob("*"):
            try:
                os.remove(file)
            except OSError:
                pass


def test_evidence_upload_success(client: TestClient, tmp_path):
    """Test successful evidence file upload."""
    email = f"ev_success_{uuid.uuid4().hex[:6]}@test.com"
    
    # 1. Registro y login
    client.post("/auth/register", json={"email": email, "password": "pass", "full_name": "Ev User"})
    client.post("/auth/login", json={"email": email, "password": "pass"})
    
    # 2. Crear cliente
    res_client = client.post("/api/clients", json={"name": "Ev Client", "sector": "Tech", "country": "US", "confidentiality_level": "medium"})
    assert res_client.status_code == status.HTTP_200_OK
    client_id = res_client.json()["id"]
    
    # 3. Obtener standard_id del seed
    db = SessionLocal()
    std = db.query(Standard).filter(Standard.code == "ISO9001-DEMO").first()
    assert std is not None, "Standard ISO9001-DEMO no encontrado. Ejecuta seed_demo.py primero."
    standard_id = str(std.id)
    db.close()
    
    # 4. Crear auditoría
    res_audit = client.post("/api/audits", json={
        "client_id": client_id,
        "standard_id": standard_id,
        "name": "Ev Audit",
        "status": "planned"
    })
    assert res_audit.status_code == status.HTTP_200_OK
    audit_id = res_audit.json()["id"]

    # 5. Subir evidencia usando el audit_id real
    test_file_path = tmp_path / "test_evidence.txt"
    test_file_path.write_text("Test evidence content")
    
    with open(test_file_path, "rb") as f:
        response = client.post(
            "/api/evidences",
            files={"file": ("test_evidence.txt", f, "text/plain")},
            data={"audit_id": audit_id},
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_evidence.txt"
    assert data["extraction_status"] == "pending"


def test_evidence_upload_invalid_file_type(client: TestClient, tmp_path):
    """Test upload with invalid file type."""
    email = f"ev_invalid_{uuid.uuid4().hex[:6]}@test.com"
    client.post("/auth/register", json={"email": email, "password": "pass", "full_name": "Ev User"})
    client.post("/auth/login", json={"email": email, "password": "pass"})
    
    # Necesitamos un audit_id válido para que la validación de tipo de archivo sea la que falle, no la FK
    res_client = client.post("/api/clients", json={"name": "Ev Client", "sector": "Tech", "country": "US", "confidentiality_level": "medium"})
    client_id = res_client.json()["id"]
    
    db = SessionLocal()
    std = db.query(Standard).filter(Standard.code == "ISO9001-DEMO").first()
    standard_id = str(std.id)
    db.close()
    
    res_audit = client.post("/api/audits", json={"client_id": client_id, "standard_id": standard_id, "name": "Ev Audit", "status": "planned"})
    audit_id = res_audit.json()["id"]

    test_file_path = tmp_path / "test.exe"
    test_file_path.write_bytes(b"fake executable")
    
    with open(test_file_path, "rb") as f:
        response = client.post(
            "/api/evidences",
            files={"file": ("test.exe", f, "application/x-msdownload")},
            data={"audit_id": audit_id},
        )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_evidence_upload_missing_audit_id(client: TestClient, tmp_path):
    """Test upload without audit_id."""
    test_file_path = tmp_path / "test.txt"
    test_file_path.write_text("content")
    
    with open(test_file_path, "rb") as f:
        response = client.post(
            "/api/evidences",
            files={"file": ("test.txt", f, "text/plain")},
        )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY