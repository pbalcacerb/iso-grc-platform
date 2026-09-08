"""Tests de integración para el Módulo 6.1 (Pre-Auditoría Documental ISO 19011 §6.2)."""
import io
import uuid
import pytest
import argon2

from app.models import Tenant, User, Membership


def test_health(client):
    """Valida el estado de salud del servidor (endpoint /health)."""
    response = client.get("/health")
    assert response.status_code == 200, f"Health check falló con status: {response.status_code}"
    data = response.json()
    assert "status" in data, f"Respuesta de health inesperada: {data}"
    assert data["status"] in ["ok", "healthy"], f"Estado de salud no es ok/healthy: {data['status']}"


def test_login(client, db_session):
    """Valida autenticación en /web/login emitiendo cookie de sesión y redirección 303."""
    hasher = argon2.PasswordHasher()
    email = f"pre_audit_login_{uuid.uuid4().hex[:6]}@grc.com"
    password = "SecretPassword123!"
    
    tenant = Tenant(name="Test Tenant Login", slug=f"tenant-{uuid.uuid4().hex[:6]}")
    db_session.add(tenant)
    db_session.flush()
    
    user = User(email=email, password_hash=hasher.hash(password), full_name="Test PreAudit Login User")
    db_session.add(user)
    db_session.flush()
    
    membership = Membership(user_id=user.id, tenant_id=tenant.id, role="owner")
    db_session.add(membership)
    db_session.commit()

    login_payload = {
        "email": email,
        "password": password
    }

    response = client.post(
        "/web/login",
        data=login_payload,
        follow_redirects=False
    )

    assert response.status_code == 303, f"Login falló con status {response.status_code}, esperado 303"
    redirect_location = response.headers.get("location", "")
    assert redirect_location == "/dashboard", f"Redirección incorrecta tras login: {redirect_location}"
    assert "error=invalid" not in redirect_location, f"Credenciales rechazadas para {email}"
    assert "session" in response.cookies or "session" in client.cookies, "Cookie de sesión no encontrada"


def test_upload_pre_audit_document(authenticated_client):
    """Valida la carga de documentos de pre-auditoría con redirección HITL a /pre-audit/review/{report_id}."""
    dummy_pdf = io.BytesIO(b"%PDF-1.4 Content of test policy ISO 27001 document")
    
    files = [
        ("files", ("iso_policy_test.pdf", dummy_pdf, "application/pdf"))
    ]
    data = {
        "standard_code": "ISO27001"
    }

    response = authenticated_client.post(
        "/api/pre-analysis/upload",
        files=files,
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 303, f"Upload falló con status {response.status_code}. Respuesta: {response.text[:200]}"
    location = response.headers.get("location", "")
    assert location.startswith("/pre-audit/review/"), f"Redirección HITL esperada a '/pre-audit/review/...', recibida: '{location}'"