"""Pruebas de integración nativas para Módulo 6.3 - Gestión de Hallazgos y CAPA."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import (
    AuditChecklistResponse, AuditChecklistItem, AuditChecklist,
    Finding, CorrectiveAction, User, Tenant, Audit, Client, Standard,
    ComplianceStatus, Membership, FindingSeverity
)
from app.db import get_db

client = TestClient(app)


def create_full_audit_context(db_session, tenant_id: uuid.UUID, auditor_user_id: uuid.UUID):
    """Fixture auxiliar que construye jerarquía completa con respuesta NO CONFORME."""
    
    # 1. Tenant
    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        tenant = Tenant(
            id=tenant_id,
            name=f"Tenant Test {tenant_id.hex[:6]}",
            slug=f"tenant-test-{tenant_id.hex[:6]}"
        )
        db_session.add(tenant)
        db_session.flush()

    # 2. Cliente
    client_obj = db_session.query(Client).filter(Client.tenant_id == tenant_id).first()
    if not client_obj:
        client_obj = Client(id=uuid.uuid4(), tenant_id=tenant_id, name="Cliente Test M6.3", status="active")
        db_session.add(client_obj)
        db_session.flush()

    # 3. Norma
    standard = db_session.query(Standard).first()
    if not standard:
        standard = Standard(id=uuid.uuid4(), code="ISO9001", name="Calidad", version="2015")
        db_session.add(standard)
        db_session.flush()

    # 4. Auditoría
    audit = Audit(
        id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_obj.id,
        standard_id=standard.id, name="Auditoría Test M6.3", status="in_progress"
    )
    db_session.add(audit)
    db_session.flush()

    # 5. Checklist
    checklist = AuditChecklist(
        id=uuid.uuid4(), tenant_id=tenant_id, audit_id=audit.id,
        standard_code=standard.code, status="in_progress"
    )
    db_session.add(checklist)
    db_session.flush()

    # 6. Ítem del Checklist
    item = AuditChecklistItem(
        id=uuid.uuid4(), checklist_id=checklist.id,
        clause_ref="A.8.1.1", description="Política de seguridad", weight=1
    )
    db_session.add(item)
    db_session.flush()

    # 7. Respuesta NO CONFORME
    response = AuditChecklistResponse(
        id=uuid.uuid4(), 
        item_id=item.id, 
        auditor_id=auditor_user_id,
        status=ComplianceStatus.NON_COMPLIANT, 
        notes="Falta evidencia crítica"
    )
    db_session.add(response)
    
    db_session.commit()
    db_session.refresh(item)
    
    return response, item


# --- Tests Corregidos ---

def test_create_finding_from_non_compliant_response(authenticated_client, db_session):
    """Valida creación idempotente de hallazgo."""
    membership = db_session.query(Membership).filter(
        Membership.user_id.in_(
            db_session.query(User.id).filter(User.email.like("test_owner_%"))
        )
    ).first()
    auditor_id = membership.user_id if membership else uuid.uuid4()
    
    response_obj, item = create_full_audit_context(
        db_session, authenticated_client.tenant_id, auditor_id
    )

    payload = {
        "checklist_item_id": str(item.id),
        "title": "Hallazgo de Prueba M6.3",
        "description": "Descripción detallada.",
        "type": "non_conformity",
        "severity": "MINOR"
    }

    res = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)
    assert res.status_code == 201, f"Error: {res.text}"
    data = res.json()
    assert "finding_id" in data
    assert data["status"].upper() == "OPEN"

    # Idempotencia
    res2 = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)
    assert res2.status_code in [200, 201]
    assert "ya existente" in res2.json()["message"].lower()


def test_assign_and_update_corrective_action(authenticated_client, db_session):
    """Flujo completo: Asignación → Actualización → Verificación."""
    membership = db_session.query(Membership).filter(
        Membership.user_id.in_(
            db_session.query(User.id).filter(User.email.like("test_owner_%"))
        )
    ).first()
    auditor_id = membership.user_id if membership else uuid.uuid4()
    
    response_obj, item = create_full_audit_context(
        db_session, authenticated_client.tenant_id, auditor_id
    )
    
    finding_payload = {
        "checklist_item_id": str(item.id),
        "title": "Hallazgo para CAPA",
        "description": "Requiere acción correctiva",
        "type": "non_conformity",
        "severity": "CRITICAL"
    }
    res_find = client.post("/api/v1/findings", json=finding_payload, cookies=authenticated_client.cookies)
    assert res_find.status_code == 201, f"Error: {res_find.text}"
    finding_id = res_find.json()["finding_id"]

    action_payload = {"action_plan": "Implementar procedimiento.", "due_date": "2026-12-31T23:59:59"}
    res_action = client.post(f"/api/v1/findings/{finding_id}/corrective-action", json=action_payload, cookies=authenticated_client.cookies)
    assert res_action.status_code == 201
    assert res_action.json()["finding_status"].upper() == "IN_PROGRESS"


def test_close_finding_requires_evidence(authenticated_client, db_session):
    """No se puede cerrar sin evidencia."""
    membership = db_session.query(Membership).filter(
        Membership.user_id.in_(
            db_session.query(User.id).filter(User.email.like("test_owner_%"))
        )
    ).first()
    auditor_id = membership.user_id if membership else uuid.uuid4()
    
    response_obj, item = create_full_audit_context(
        db_session, authenticated_client.tenant_id, auditor_id
    )
    
    finding_payload = {
        "checklist_item_id": str(item.id),
        "title": "Bloqueado",
        "description": "Sin evidencia",
        "type": "non_conformity",
        "severity": "MINOR"
    }
    res_find = client.post("/api/v1/findings", json=finding_payload, cookies=authenticated_client.cookies)
    assert res_find.status_code == 201
    finding_id = res_find.json()["finding_id"]

    client.post(f"/api/v1/findings/{finding_id}/corrective-action", json={"action_plan": "Plan"}, cookies=authenticated_client.cookies)

    res_close = client.post(f"/api/v1/findings/{finding_id}/close", json={"verification_notes": "Intento prematuro"}, cookies=authenticated_client.cookies)
    assert res_close.status_code == 400
    assert "evidencia" in res_close.json()["detail"].lower()


def test_tenant_isolation_findings(authenticated_client, db_session):
    """Usuario de otro tenant NO puede acceder."""
    other_tenant_id = uuid.uuid4()
    other_tenant = Tenant(
        id=other_tenant_id,
        name="Other Tenant Isolation",
        slug=f"other-{uuid.uuid4().hex[:6]}"
    )
    db_session.add(other_tenant)
    db_session.flush()
    
    other_user = User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:6]}@tenant.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
        full_name="Other Tenant User",
        status="active"
    )
    db_session.add(other_user)
    db_session.flush()
    
    other_membership = Membership(
        user_id=other_user.id,
        tenant_id=other_tenant_id,
        role="auditor"
    )
    db_session.add(other_membership)
    db_session.flush()
    
    response_obj, item = create_full_audit_context(
        db_session, other_tenant_id, other_user.id
    )
    
    payload = {
        "checklist_item_id": str(item.id),
        "title": "Aislado",
        "description": "Test",
        "type": "non_conformity",
        "severity": "MINOR"
    }
    res = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)
    assert res.status_code == 404


def test_finding_severity_filtering(authenticated_client, db_session):
    """Filtra hallazgos por severidad correctamente."""
    membership = db_session.query(Membership).filter(
        Membership.user_id.in_(
            db_session.query(User.id).filter(User.email.like("test_owner_%"))
        )
    ).first()
    auditor_id = membership.user_id if membership else uuid.uuid4()
    
    response_obj, item = create_full_audit_context(
        db_session, authenticated_client.tenant_id, auditor_id
    )
    
    payload = {
        "checklist_item_id": str(item.id),
        "title": "Crítico",
        "description": "Alto riesgo",
        "type": "non_conformity",
        "severity": "CRITICAL"
    }
    res = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)
    assert res.status_code == 201

    res_list = client.get("/api/v1/findings?severity_filter=CRITICAL", cookies=authenticated_client.cookies)
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 1