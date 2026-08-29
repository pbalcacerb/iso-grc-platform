"""Tests de autorización por rol (modelo de 8 roles ISO, WP2.5-3.5)."""
import uuid

import argon2
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Audit, Client, Membership, Standard, Tenant, User

client = TestClient(app)
hasher = argon2.PasswordHasher()


def _create_user_with_role(role: str) -> tuple[str, uuid.UUID]:
    email = f"{role}_{uuid.uuid4().hex[:6]}@test.com"
    db = SessionLocal()
    tenant = Tenant(name="T", slug=f"s-{uuid.uuid4().hex[:6]}")
    db.add(tenant)
    db.flush()
    user = User(email=email, password_hash=hasher.hash("pass123"), full_name="Role Test")
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=role))
    db.commit()
    tid = tenant.id
    db.close()
    return email, tid


def _create_audit(tenant_id: uuid.UUID) -> str:
    db = SessionLocal()
    std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="Std")
    db.add(std)
    db.flush()
    cli = Client(tenant_id=tenant_id, name="C")
    db.add(cli)
    db.flush()
    audit = Audit(tenant_id=tenant_id, client_id=cli.id, standard_id=std.id, name="A")
    db.add(audit)
    db.commit()
    audit_id = str(audit.id)
    db.close()
    return audit_id


# ====== LOGOUT Y PERMISOS BÁSICOS DE CARGA ======

def test_logout_clears_session():
    email, _ = _create_user_with_role("observer")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/web/logout", follow_redirects=False)
    assert resp.status_code == 303


def test_observer_cannot_upload_evidence():
    """Observer (experto/observador) solo lee, no carga evidencias."""
    email, tid = _create_user_with_role("observer")
    audit_id = _create_audit(tid)
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(
        f"/audit/{audit_id}/analyze",
        files={"file": ("e.txt", b"texto", "text/plain")},
    )
    assert resp.status_code == 403


def test_auditor_can_upload_evidence():
    email, tid = _create_user_with_role("auditor")
    audit_id = _create_audit(tid)
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(
        f"/audit/{audit_id}/analyze",
        files={"file": ("e.txt", b"texto", "text/plain")},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_client_responsible_can_upload_evidence():
    """El responsable del cliente sí puede cargar evidencias de su auditoría."""
    email, tid = _create_user_with_role("client_responsible")
    audit_id = _create_audit(tid)
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(
        f"/audit/{audit_id}/analyze",
        files={"file": ("e.txt", b"texto", "text/plain")},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_client_sponsor_cannot_upload_evidence():
    """El sponsor del cliente solo tiene vista ejecutiva, no carga evidencias."""
    email, tid = _create_user_with_role("client_sponsor")
    audit_id = _create_audit(tid)
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(
        f"/audit/{audit_id}/analyze",
        files={"file": ("e.txt", b"texto", "text/plain")},
    )
    assert resp.status_code == 403


# ====== COLA DE REVISIÓN (WP2.5-3) ======

def test_coordinator_can_access_review_queue():
    """El revisor (coordinator) sí puede ver la cola de revisión."""
    email, _ = _create_user_with_role("coordinator")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/review-queue")
    assert resp.status_code == 200


def test_lead_auditor_can_access_review_queue():
    email, _ = _create_user_with_role("lead_auditor")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/review-queue")
    assert resp.status_code == 200


def test_client_sponsor_cannot_access_review_queue():
    email, _ = _create_user_with_role("client_sponsor")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/review-queue", follow_redirects=False)
    assert resp.status_code == 403


def test_client_responsible_cannot_access_review_queue():
    email, _ = _create_user_with_role("client_responsible")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/review-queue", follow_redirects=False)
    assert resp.status_code == 403


def test_observer_cannot_access_review_queue():
    """Observer es solo lectura interna, no gestiona la cola."""
    email, _ = _create_user_with_role("observer")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/review-queue", follow_redirects=False)
    assert resp.status_code == 403


# ====== CICLO DEL ÍTEM: APROBAR / REABRIR (WP2.5-3.5) ======

def test_coordinator_cannot_approve_item():
    """Regla clave del modelo: el coordinator NO aprueba, solo el lead_auditor/owner."""
    email, _ = _create_user_with_role("coordinator")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(f"/audit/{uuid.uuid4()}/item/{uuid.uuid4()}/approve")
    assert resp.status_code == 403


def test_lead_auditor_can_approve_item():
    """El lead_auditor sí tiene approve_item."""
    email, tid = _create_user_with_role("lead_auditor")
    # No creamos audit real porque el 404 vendría antes del 403; basta con
    # confirmar que la dependencia de permiso lo deja pasar (303 o 404, no 403).
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(f"/audit/{uuid.uuid4()}/item/{uuid.uuid4()}/approve")
    assert resp.status_code != 403