"""Tests de autorización por rol."""
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


def test_logout_clears_session():
    email, _ = _create_user_with_role("viewer")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/web/logout", follow_redirects=False)
    assert resp.status_code == 303


def test_viewer_cannot_upload_evidence():
    email, tid = _create_user_with_role("viewer")
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