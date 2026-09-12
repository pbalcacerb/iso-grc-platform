"""Pruebas de integración nativas para Módulo 6.4 - Cierre Formal de Auditoría."""
import uuid
import pytest
from app.models import User, Membership, Finding, CorrectiveAction, CAPAStatus, FindingSeverity


def create_closed_finding_context(db_session, tenant_id: uuid.UUID):
    """Crea contexto completo con hallazgos cerrados para tests de cierre."""
    
    membership = db_session.query(Membership).filter(
        Membership.tenant_id == tenant_id
    ).first()
    if not membership:
        pytest.skip(f"No hay membresías para tenant {tenant_id}")
    
    auditor_id = membership.user_id
    
    from tests.test_findings_management import create_full_audit_context
    response_obj, item = create_full_audit_context(db_session, tenant_id, auditor_id)
    
    finding = Finding(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        audit_id=response_obj.item.checklist.audit_id,
        checklist_item_id=item.id,
        title="Hallazgo de Prueba Cierre",
        description="Para test de cierre",
        type="non_conformity",
        severity="MINOR",
        status="RESOLVED"
    )
    db_session.add(finding)
    db_session.flush()
    
    action = CorrectiveAction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        finding_id=finding.id,
        assigned_to=auditor_id,
        action_plan="Acción implementada",
        evidence_notes="Evidencia adjunta",
        status=CAPAStatus.VERIFIED.value
    )
    db_session.add(action)
    db_session.commit()
    
    return finding.audit_id, finding.id, action.id


def test_closing_readiness_endpoint(authenticated_client, db_session):
    """Verifica endpoint de readiness para cierre."""
    tenant_id = authenticated_client.tenant_id
    audit_id, _, _ = create_closed_finding_context(db_session, tenant_id)
    
    res = authenticated_client.get(f"/api/v1/audits/{audit_id}/closure-readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["can_close"] is True
    assert data["open_findings_count"] == 0


def test_close_audit_successfully(authenticated_client, db_session):
    """Cierra auditoría exitosamente cuando todo está resuelto."""
    tenant_id = authenticated_client.tenant_id
    audit_id, _, _ = create_closed_finding_context(db_session, tenant_id)
    
    res = authenticated_client.post(f"/api/v1/audits/{audit_id}/close", json={
        "closing_summary": "Auditoría cerrada exitosamente. Todos los hallazgos resueltos."
    })
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_close_audit_blocked_by_open_findings(authenticated_client, db_session):
    """No se puede cerrar si hay hallazgos abiertos."""
    tenant_id = authenticated_client.tenant_id
    audit_id, finding_id, _ = create_closed_finding_context(db_session, tenant_id)
    
    finding = db_session.query(Finding).filter(Finding.id == finding_id).first()
    finding.status = "OPEN"
    db_session.commit()
    
    res = authenticated_client.post(f"/api/v1/audits/{audit_id}/close", json={
        "closing_summary": "Intento de cierre con hallazgos abiertos"
    })
    assert res.status_code == 409
    assert "open_findings" in res.json()["blockers"][0].lower()


def test_close_audit_blocked_by_pending_capas(authenticated_client, db_session):
    """No se puede cerrar si hay CAPAs pendientes."""
    tenant_id = authenticated_client.tenant_id
    audit_id, _, action_id = create_closed_finding_context(db_session, tenant_id)
    
    action = db_session.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
    action.status = CAPAStatus.PLANNED.value
    db_session.commit()
    
    res = authenticated_client.post(f"/api/v1/audits/{audit_id}/close", json={
        "closing_summary": "Intento de cierre con CAPAs pendientes"
    })
    assert res.status_code == 409
    assert "pending_capas" in res.json()["blockers"][0].lower()


def test_close_audit_idempotent(authenticated_client, db_session):
    """Cerrar dos veces la misma auditoría retorna 200 OK."""
    tenant_id = authenticated_client.tenant_id
    audit_id, _, _ = create_closed_finding_context(db_session, tenant_id)
    
    res1 = authenticated_client.post(f"/api/v1/audits/{audit_id}/close", json={
        "closing_summary": "Primer cierre"
    })
    assert res1.status_code == 200
    
    res2 = authenticated_client.post(f"/api/v1/audits/{audit_id}/close", json={
        "closing_summary": "Segundo cierre"
    })
    assert res2.status_code == 200