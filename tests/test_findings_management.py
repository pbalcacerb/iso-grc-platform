"""
Pruebas de integración nativas para Módulo 6.3 - Gestión de Hallazgos y CAPA (ISO 19011 §6.5).
Usa authenticated_client.tenant_id inyectado desde la fixture.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import (
    AuditChecklistResponse, 
    AuditChecklistItem, 
    AuditChecklist,
    Finding, 
    CorrectiveAction, 
    User, 
    Tenant,
    Audit,
    Client,
    Standard,
    ComplianceStatus
)
from app.db import get_db

client = TestClient(app)

def create_full_audit_context(db_session, tenant_id):
    """Crea contexto de auditoría VINCULADO EXPLÍCITAMENTE AL TENANT_ID."""
    
    # 1. Standard
    standard = db_session.query(Standard).first()
    if not standard:
        standard = Standard(id=uuid.uuid4(), code="ISO9001", name="Calidad", version="2015")
        db_session.add(standard)
        db_session.flush()

    # 2. Client (VINCULADO AL TENANT DEL TEST)
    client_obj = Client(
        id=uuid.uuid4(), 
        tenant_id=tenant_id,
        name="Cliente Test M6.3", 
        sector="Tech", 
        country="DO", 
        confidentiality_level="internal",
        status="active"
    )
    db_session.add(client_obj)
    db_session.flush()

    # 3. Audit
    audit = Audit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_obj.id,
        standard_id=standard.id,
        name="Auditoría Test M6.3",
        status="in_progress"
    )
    db_session.add(audit)
    db_session.flush()

    # 4. Checklist
    checklist = AuditChecklist(
        id=uuid.uuid4(),
        audit_id=audit.id,
        standard_code=standard.code,
        tenant_id=tenant_id,
        status="in_progress"
    )
    db_session.add(checklist)
    db_session.flush()

    # 5. Item
    item = AuditChecklistItem(
        id=uuid.uuid4(),
        checklist_id=checklist.id,
        clause_ref="A.8.1.1",
        description="Política de seguridad",
        weight=1
    )
    db_session.add(item)
    db_session.flush()

    # 6. Auditor User
    auditor = User(
        id=uuid.uuid4(),
        email=f"auditor_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="dummy_hash_for_test",
        full_name="Auditor de Prueba",
        status="active"
    )
    db_session.add(auditor)
    db_session.flush()

    # 7. Response
    response = AuditChecklistResponse(
        id=uuid.uuid4(),
        item_id=item.id,
        auditor_id=auditor.id,
        status=ComplianceStatus.NON_COMPLIANT,
        notes="Falta evidencia crítica"
    )
    db_session.add(response)
    db_session.commit()
    
    return response

# --- Tests ---

def test_create_finding_from_non_compliant_response(authenticated_client, db_session):
    """Valida la creación idempotente de un hallazgo."""
    
    # ✅ USAR TENANT_ID INYECTADO DIRECTAMENTE DESDE LA FIXTURE
    tenant_id = authenticated_client.tenant_id

    response_obj = create_full_audit_context(db_session, tenant_id)

    payload = {
        "response_id": str(response_obj.id),
        "title": "Hallazgo de Prueba M6.3",
        "description": "Descripción detallada del incumplimiento.",
        "severity": "MAJOR"
    }

    res = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)

    assert res.status_code == 201, f"Error: {res.text}"
    data = res.json()
    assert "finding_id" in data
    assert data["status"] == "OPEN"

    # Validar Idempotencia
    res2 = client.post("/api/v1/findings", json=payload, cookies=authenticated_client.cookies)
    assert res2.status_code in [200, 201], f"Esperaba 200 o 201, obtuvo {res2.status_code}: {res2.text}"
    assert "ya existente" in res2.json()["message"].lower()

def test_assign_and_update_corrective_action(authenticated_client, db_session):
    """Flujo completo: Asignación → Actualización → Verificación de estado."""
    tenant_id = authenticated_client.tenant_id

    response_obj = create_full_audit_context(db_session, tenant_id)
    
    finding_payload = {
        "response_id": str(response_obj.id),
        "title": "Hallazgo para CAPA",
        "description": "Requiere acción correctiva",
        "severity": "CRITICAL"
    }
    res_find = client.post("/api/v1/findings", json=finding_payload, cookies=authenticated_client.cookies)
    assert res_find.status_code == 201, f"Error al crear hallazgo: {res_find.text}"
    finding_id = res_find.json()["finding_id"]

    action_payload = {
        "due_date": "2026-12-31T23:59:59"
    }
    res_action = client.post(f"/api/v1/findings/{finding_id}/corrective-action", json=action_payload, cookies=authenticated_client.cookies)
    assert res_action.status_code == 201, f"Error al asignar CAPA: {res_action.text}"
    action_id = res_action.json()["action_id"]
    
    assert res_action.json()["finding_status"] == "IN_PROGRESS"

    update_payload = {
        "evidence_of_implementation": "Link al documento v2.0",
        "status": "VERIFIED"
    }
    res_update = client.patch(f"/api/v1/findings/corrective-actions/{action_id}", json=update_payload, cookies=authenticated_client.cookies)
    assert res_update.status_code == 200

def test_close_finding_requires_evidence(authenticated_client, db_session):
    """No se puede cerrar un hallazgo sin evidencia."""
    tenant_id = authenticated_client.tenant_id

    response_obj = create_full_audit_context(db_session, tenant_id)
    
    finding_payload = {
        "response_id": str(response_obj.id),
        "title": "Hallazgo Bloqueado",
        "description": "Sin evidencia",
        "severity": "MINOR"
    }
    
    res_find = client.post("/api/v1/findings", json=finding_payload, cookies=authenticated_client.cookies)
    assert res_find.status_code == 201
    finding_id = res_find.json()["finding_id"]

    action_payload = {"action_plan": "Plan sin ejecutar"}
    client.post(f"/api/v1/findings/{finding_id}/corrective-action", json=action_payload, cookies=authenticated_client.cookies)

    close_payload = {"verification_notes": "Intento de cierre prematuro"}
    res_close = client.post(f"/api/v1/findings/{finding_id}/close", json=close_payload, cookies=authenticated_client.cookies)
    
    assert res_close.status_code == 400
    assert "evidencia" in res_close.json()["detail"].lower()

def test_tenant_isolation_findings(authenticated_client, db_session):
    """Usuario de otro tenant NO puede ver ni modificar hallazgos ajenos."""
    tenant_id = authenticated_client.tenant_id

    response_obj = create_full_audit_context(db_session, tenant_id)
    
    finding_payload = {
        "response_id": str(response_obj.id),
        "title": "Hallazgo Aislado",
        "description": "Solo visible para mi tenant",
        "severity": "MINOR"
    }
    
    res_create = client.post("/api/v1/findings", json=finding_payload, cookies=authenticated_client.cookies)
    assert res_create.status_code == 201, f"Error al crear hallazgo para aislamiento: {res_create.text}"
    
    res_list = client.get("/api/v1/findings", cookies=authenticated_client.cookies)
    assert res_list.status_code == 200
    findings = res_list.json()["findings"]
    
    assert len(findings) >= 1

def test_finding_severity_filtering(authenticated_client, db_session):
    """Filtra hallazgos por severidad correctamente."""
    tenant_id = authenticated_client.tenant_id

    response_obj = create_full_audit_context(db_session, tenant_id)
    
    payload_critical = {
        "response_id": str(response_obj.id),
        "title": "Hallazgo Crítico",
        "description": "Alto riesgo",
        "severity": "CRITICAL"
    }
    res_create = client.post("/api/v1/findings", json=payload_critical, cookies=authenticated_client.cookies)
    assert res_create.status_code == 201, f"Error al crear hallazgo crítico: {res_create.text}"

    res = client.get("/api/v1/findings?severity_filter=CRITICAL", cookies=authenticated_client.cookies)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert all(f["severity"] == "CRITICAL" for f in data["findings"])