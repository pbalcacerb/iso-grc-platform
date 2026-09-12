"""Módulo de gestión de hallazgos y acciones correctivas (ISO 19011 §6.5)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.db import get_db
from app.models import (
    Finding, CorrectiveAction, FindingAttachment,
    AuditChecklist, AuditChecklistItem, AuditChecklistResponse,
    Audit, Membership, User,
    FindingSeverity, FindingStatus, CAPAStatus, ComplianceStatus
)
from app.permissions import require_perm

router = APIRouter(prefix="/api/v1/findings", tags=["Findings & CAPA"])


# --- Schemas Pydantic ---

class FindingCreateInput(BaseModel):
    checklist_item_id: UUID
    title: str
    description: str
    type: Optional[str] = "non_conformity"
    severity: Optional[FindingSeverity] = FindingSeverity.MINOR


class FindingUpdateInput(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[FindingSeverity] = None
    status: Optional[FindingStatus] = None


class CorrectiveActionCreateInput(BaseModel):
    action_plan: str = "Plan de acción correctiva"
    assigned_to: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None  # Compatibilidad legacy
    due_date: Optional[datetime] = None
    deadline: Optional[datetime] = None  # Compatibilidad legacy


class CorrectiveActionUpdateInput(BaseModel):
    action_plan: Optional[str] = None
    evidence_notes: Optional[str] = None
    evidence_of_implementation: Optional[str] = None
    verification_notes: Optional[str] = None
    status: Optional[CAPAStatus] = None


class FindingCloseInput(BaseModel):
    verification_notes: str


# --- Endpoints ---

@router.post("", status_code=201)
def create_finding(
    body: FindingCreateInput,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Crea un hallazgo formal validando origen, severidad y tenant."""
    
    item = db.query(AuditChecklistItem).join(
        AuditChecklist, AuditChecklistItem.checklist_id == AuditChecklist.id
    ).join(
        Audit, AuditChecklist.audit_id == Audit.id
    ).filter(
        AuditChecklistItem.id == body.checklist_item_id,
        Audit.tenant_id == membership.tenant_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Ítem de checklist no encontrado o sin permisos")

    response = db.query(AuditChecklistResponse).filter(
        AuditChecklistResponse.item_id == body.checklist_item_id,
        AuditChecklistResponse.status.in_([ComplianceStatus.NON_COMPLIANT, ComplianceStatus.OBSERVATION])
    ).first()
    
    if not response:
        raise HTTPException(
            status_code=400, 
            detail="Solo se pueden crear hallazgos desde respuestas No Conformes u Observaciones"
        )

    existing = db.query(Finding).filter(
        Finding.checklist_item_id == body.checklist_item_id
    ).first()
    if existing:
        return {
            "message": "Hallazgo ya existente para este ítem",
            "finding_id": str(existing.id),
            "status": existing.status
        }

    severity_val = body.severity.value if hasattr(body.severity, 'value') else str(body.severity) if body.severity else "MINOR"

    finding = Finding(
        tenant_id=membership.tenant_id,
        audit_id=item.checklist.audit_id,
        checklist_item_id=body.checklist_item_id,
        title=body.title,
        description=body.description,
        type=body.type or "non_conformity",
        severity=severity_val,
        status=FindingStatus.OPEN.value
    )
    
    db.add(finding)
    db.commit()
    db.refresh(finding)
    
    return {
        "message": "Hallazgo creado exitosamente",
        "finding_id": str(finding.id),
        "status": finding.status
    }


@router.get("")
def list_findings(
    audit_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("read_audit"))
):
    """Lista hallazgos filtrados con aislamiento multi-tenant estricto."""
    query = db.query(Finding).filter(Finding.tenant_id == membership.tenant_id)
    
    if audit_id:
        query = query.filter(Finding.audit_id == audit_id)
    if status_filter:
        query = query.filter(Finding.status == status_filter)
    if severity_filter:
        query = query.filter(Finding.severity == severity_filter)
        
    findings = query.order_by(Finding.created_at.desc()).all()
    
    result = []
    for f in findings:
        result.append({
            "id": str(f.id),
            "audit_id": str(f.audit_id),
            "checklist_item_id": str(f.checklist_item_id),
            "title": f.title,
            "description": f.description,
            "type": f.type,
            "severity": f.severity,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })
        
    return {"total": len(result), "findings": result}


@router.patch("/{finding_id}")
def update_finding(
    finding_id: UUID,
    body: FindingUpdateInput,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Actualiza estado, severidad o contenido de un hallazgo."""
    finding = db.query(Finding).filter(
        Finding.id == finding_id, 
        Finding.tenant_id == membership.tenant_id
    ).first()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    if body.title is not None: finding.title = body.title
    if body.description is not None: finding.description = body.description
    if body.severity is not None: finding.severity = body.severity.value if hasattr(body.severity, 'value') else str(body.severity)
    if body.status is not None: finding.status = body.status.value if hasattr(body.status, 'value') else str(body.status)
    
    finding.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Hallazgo actualizado", "finding_id": str(finding.id), "status": finding.status}


@router.post("/{finding_id}/corrective-action", status_code=201)
def assign_corrective_action(
    finding_id: UUID,
    body: CorrectiveActionCreateInput,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Asigna una acción correctiva (CAPA) a un hallazgo con fallbacks seguros."""
    finding = db.query(Finding).filter(
        Finding.id == finding_id,
        Finding.tenant_id == membership.tenant_id
    ).first()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    assigned_user_id = body.assigned_to or body.assigned_to_id or membership.user_id
    due_date_val = body.due_date or body.deadline
    plan_text = body.action_plan.strip() if body.action_plan and body.action_plan.strip() else "Plan de acción correctiva"

    action = CorrectiveAction(
        tenant_id=membership.tenant_id,
        finding_id=finding.id,
        assigned_to=assigned_user_id,
        action_plan=plan_text,
        due_date=due_date_val,
        status=CAPAStatus.PLANNED.value
    )
    
    db.add(action)
    
    if finding.status == FindingStatus.OPEN.value:
        finding.status = FindingStatus.IN_PROGRESS.value
        finding.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(action)
    
    return {
        "message": "Acción correctiva asignada",
        "action_id": str(action.id),
        "finding_id": str(finding.id),
        "finding_status": finding.status,
        "action_status": action.status
    }


@router.patch("/corrective-actions/{action_id}")
def update_corrective_action(
    action_id: UUID,
    body: CorrectiveActionUpdateInput,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Actualiza progreso, evidencias o estado de una acción correctiva."""
    action = db.query(CorrectiveAction).join(Finding).filter(
        CorrectiveAction.id == action_id,
        Finding.tenant_id == membership.tenant_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Acción correctiva no encontrada")

    if body.action_plan is not None: action.action_plan = body.action_plan
    
    evidence_val = body.evidence_notes or body.evidence_of_implementation
    if evidence_val is not None: action.evidence_notes = evidence_val

    if body.status is not None: 
        status_val = body.status.value if hasattr(body.status, 'value') else str(body.status)
        action.status = status_val
        
        if status_val in [CAPAStatus.VERIFIED.value, CAPAStatus.COMPLETED.value]:
            finding = action.finding
            if finding:
                finding.status = FindingStatus.RESOLVED.value
                finding.updated_at = datetime.now(timezone.utc)

    action.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Acción actualizada", "action_id": str(action.id), "action_status": action.status}


@router.post("/{finding_id}/close")
def close_finding(
    finding_id: UUID,
    body: FindingCloseInput,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Cierra formalmente un hallazgo previa verificación de evidencia."""
    finding = db.query(Finding).filter(
        Finding.id == finding_id,
        Finding.tenant_id == membership.tenant_id
    ).first()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    actions = db.query(CorrectiveAction).filter(CorrectiveAction.finding_id == finding_id).all()
    if not actions:
        raise HTTPException(status_code=400, detail="No hay acciones correctivas registradas")
        
    has_evidence = any(a.evidence_notes and len(a.evidence_notes.strip()) > 0 for a in actions)
    if not has_evidence:
        raise HTTPException(status_code=400, detail="No se puede cerrar sin evidencia registrada")

    finding.status = FindingStatus.CLOSED.value
    finding.updated_at = datetime.now(timezone.utc)
    
    for action in actions:
        action.status = CAPAStatus.VERIFIED.value
        
    db.commit()
    
    return {
        "message": "Hallazgo cerrado formalmente",
        "finding_id": str(finding_id),
        "status": finding.status,
        "verification_notes": body.verification_notes
    }