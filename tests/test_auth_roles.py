"""Tests de autorización por rol (modelo de 8 roles ISO, WP2.5-3.5)."""
import uuid

import argon2
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    Audit,
    ChecklistItem,
    Clause,
    Client,
    Membership,
    QuestionPack,
    Standard,
    Tenant,
    User,
)

client = TestClient(app)
hasher = argon2.PasswordHasher()


def _create_user_with_role(role: str) -> tuple[str, uuid.UUID]:
    db = SessionLocal()
    try:
        email = f"{role}_{uuid.uuid4().hex[:6]}@test.com"
        tenant = Tenant(name="T", slug=f"s-{uuid.uuid4().hex[:6]}")
        db.add(tenant)
        db.flush()
        user = User(email=email, password_hash=hasher.hash("pass123"), full_name="Role Test")
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=role))
        db.commit()
        return email, tenant.id
    finally:
        db.close()


def _create_audit(tenant_id: uuid.UUID) -> str:
    db = SessionLocal()
    try:
        std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="Std")
        db.add(std)
        db.flush()
        cli = Client(tenant_id=tenant_id, name="C")
        db.add(cli)
        db.flush()
        audit = Audit(tenant_id=tenant_id, client_id=cli.id, standard_id=std.id, name="A")
        db.add(audit)
        db.commit()
        return str(audit.id)
    finally:
        db.close()


def _create_client_user_with_client(role: str) -> tuple[str, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Devuelve (email, tenant_id, client_id, audit_id)."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="T", slug=f"s-{uuid.uuid4().hex[:6]}")
        db.add(tenant)
        db.flush()
        std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="S")
        db.add(std)
        db.flush()
        cli = Client(tenant_id=tenant.id, name="Cliente")
        db.add(cli)
        db.flush()
        audit = Audit(tenant_id=tenant.id, client_id=cli.id, standard_id=std.id, name="Auditoria")
        db.add(audit)
        user = User(
            email=f"{role}_{uuid.uuid4().hex[:6]}@t.com",
            password_hash=hasher.hash("pass123"),
            full_name="P",
        )
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=role, client_id=cli.id))
        db.commit()
        return user.email, tenant.id, cli.id, audit.id
    finally:
        db.close()


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
    email, _ = _create_user_with_role("lead_auditor")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.post(f"/audit/{uuid.uuid4()}/item/{uuid.uuid4()}/approve")
    assert resp.status_code != 403


def test_client_portal_isolated_by_client():
    """Un responsible del cliente A NO ve auditorías del cliente B."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="T", slug=f"s-{uuid.uuid4().hex[:6]}")
        db.add(tenant)
        db.flush()
        std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="S")
        db.add(std)
        db.flush()
        ca = Client(tenant_id=tenant.id, name="A")
        db.add(ca)
        db.flush()
        cb = Client(tenant_id=tenant.id, name="B")
        db.add(cb)
        db.flush()
        db.add(Audit(tenant_id=tenant.id, client_id=ca.id, standard_id=std.id, name="Auditoria Visible A"))
        db.add(Audit(tenant_id=tenant.id, client_id=cb.id, standard_id=std.id, name="Auditoria Secreta B"))
        user = User(
            email=f"r_{uuid.uuid4().hex[:6]}@t.com",
            password_hash=hasher.hash("pass123"),
            full_name="R",
        )
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="client_responsible", client_id=ca.id))
        db.commit()
        user_email = user.email
    finally:
        db.close()

    client.post("/web/login", data={"email": user_email, "password": "pass123"})
    resp = client.get("/portal")
    assert resp.status_code == 200
    assert "Auditoria Visible A" in resp.text
    assert "Auditoria Secreta B" not in resp.text


def test_portal_golden_rule_hides_pending_review():
    """Regla de Oro: un ítem en `pending_review` NO aparece en el portal."""
    email, tid, cid, aid = _create_client_user_with_client("client_responsible")

    db = SessionLocal()
    try:
        # Crear Standard necesario para la cláusula
        std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="S")
        db.add(std)
        db.flush()

        clause = Clause(standard_id=std.id, number="5.1", title="Liderazgo")
        if hasattr(Clause, "tenant_id"):
            clause.tenant_id = tid
        db.add(clause)
        db.flush()
        
        qp = QuestionPack(clause_id=clause.id, question="¿Existe política de calidad?")
        if hasattr(QuestionPack, "tenant_id"):
            qp.tenant_id = tid
        db.add(qp)
        db.flush()

        db.add(ChecklistItem(
            tenant_id=tid, audit_id=aid, clause_id=clause.id,
            question_pack_id=qp.id, status="completed"
        ))
        db.add(ChecklistItem(
            tenant_id=tid, audit_id=aid, clause_id=clause.id,
            question_pack_id=qp.id, status="pending_review"
        ))
        db.add(ChecklistItem(
            tenant_id=tid, audit_id=aid, clause_id=clause.id,
            question_pack_id=qp.id, status="pending"
        ))
        db.commit()
    finally:
        db.close()

    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/portal")
    assert resp.status_code == 200
    assert "1/2" in resp.text


def test_sponsor_portal_no_findings():
    email, _, _, _ = _create_client_user_with_client("client_sponsor")
    client.post("/web/login", data={"email": email, "password": "pass123"})
    resp = client.get("/portal")
    assert resp.status_code == 200

def test_portal_debug_query():
    """Debug: verificar qué filtra la query del portal."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="T", slug=f"s-{uuid.uuid4().hex[:6]}")
        db.add(tenant)
        db.flush()
        std = Standard(code=f"STD-{uuid.uuid4().hex[:6]}", name="S")
        db.add(std)
        db.flush()
        ca = Client(tenant_id=tenant.id, name="A")
        db.add(ca)
        db.flush()
        
        audit = Audit(tenant_id=tenant.id, client_id=ca.id, standard_id=std.id, name="Auditoria Test")
        db.add(audit)
        
        user = User(
            email=f"debug_{uuid.uuid4().hex[:6]}@t.com",
            password_hash=hasher.hash("pass123"),
            full_name="Debug",
        )
        db.add(user)
        db.flush()
        
        membership = Membership(user_id=user.id, tenant_id=tenant.id, role="client_responsible", client_id=ca.id)
        db.add(membership)
        db.commit()
        
        print(f"\n=== DEBUG ===")
        print(f"Tenant ID: {tenant.id}")
        print(f"Client ID: {ca.id}")
        print(f"Audit ID: {audit.id} (client_id={audit.client_id})")
        print(f"Membership: tenant_id={membership.tenant_id}, client_id={membership.client_id}")
        
        # Query directa sin RLS
        audits_direct = db.query(Audit).filter(
            Audit.tenant_id == membership.tenant_id,
            Audit.client_id == membership.client_id,
        ).all()
        print(f"Auditorías encontradas (query directa): {len(audits_direct)}")
        
        # Query a través de la app
        client.post("/web/login", data={"email": user.email, "password": "pass123"})
        resp = client.get("/portal")
        print(f"Response status: {resp.status_code}")
        print(f"'Auditoria Test' in response: {'Auditoria Test' in resp.text}")
        print(f"=== END DEBUG ===\n")
        
        assert len(audits_direct) == 1, "La query directa debe encontrar 1 auditoría"
        assert "Auditoria Test" in resp.text, "El portal debe mostrar la auditoría"
    finally:
        db.close()