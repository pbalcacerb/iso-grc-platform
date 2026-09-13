"""Módulo de ejecución y cierre formal de auditoría (ISO 19011 §6.4 - §6.6)."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Audit,
    CAPAStatus,
    CorrectiveAction,
    Finding,
    FindingStatus,
    Membership,
)
from app.permissions import require_perm

router = APIRouter(tags=["Audit Execution & Closure"])


# --- Schemas Módulo 6.4 ---

class AuditCloseInput(BaseModel):
    closing_summary: Optional[str] = None
    summary: Optional[str] = None  # Alias para compatibilidad con payloads alternativos


class ClosureReadinessResponse(BaseModel):
    can_close: bool
    open_findings_count: int
    pending_capas_count: int
    blockers: List[str]


# --- Helpers de Diagnóstico y Control ---

def get_audit_closure_diagnostics(audit_id: UUID, tenant_id: UUID, db: Session) -> dict:
    """Calcula la preparación de cierre auditando hallazgos y acciones en tiempo real."""
    open_statuses = [
        FindingStatus.OPEN.value if hasattr(FindingStatus.OPEN, "value") else "OPEN",
        FindingStatus.IN_PROGRESS.value if hasattr(FindingStatus.IN_PROGRESS, "value") else "IN_PROGRESS",
        "OPEN", "open", "IN_PROGRESS", "in_progress"
    ]

    open_findings = db.query(Finding).filter(
        Finding.audit_id == audit_id,
        Finding.tenant_id == tenant_id,
        Finding.status.in_(open_statuses)
    ).all()

    pending_capa_statuses = [
        CAPAStatus.PLANNED.value if hasattr(CAPAStatus.PLANNED, "value") else "PLANNED",
        CAPAStatus.IN_PROGRESS.value if hasattr(CAPAStatus.IN_PROGRESS, "value") else "IN_PROGRESS",
        CAPAStatus.COMPLETED.value if hasattr(CAPAStatus.COMPLETED, "value") else "COMPLETED",
        "PLANNED", "planned", "IN_PROGRESS", "in_progress", "COMPLETED", "completed"
    ]

    pending_capas = db.query(CorrectiveAction).join(Finding).filter(
        Finding.audit_id == audit_id,
        Finding.tenant_id == tenant_id,
        CorrectiveAction.status.in_(pending_capa_statuses)
    ).all()

    blockers = []
    if open_findings:
        blockers.append(f"open_findings: Existen {len(open_findings)} hallazgo(s) pendientes de resolución (OPEN/IN_PROGRESS)")
    if pending_capas:
        blockers.append(f"pending_capas: Existen {len(pending_capas)} acción(es) correctiva(s) sin verificación formal (VERIFIED)")

    return {
        "can_close": len(blockers) == 0,
        "open_findings_count": len(open_findings),
        "pending_capas_count": len(pending_capas),
        "blockers": blockers
    }


def ensure_audit_not_closed(audit: Audit):
    """Guard de solo lectura: evita modificaciones si la auditoría ya fue cerrada."""
    if audit.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La auditoría se encuentra cerrada formalmente y no admite modificaciones"
        )


# --- Endpoints M6.4 ---

@router.get("/api/v1/audits/{audit_id}/closure-readiness", response_model=ClosureReadinessResponse)
@router.get("/api/v1/audit-execution/{audit_id}/closure-readiness", response_model=ClosureReadinessResponse)
def check_closure_readiness(
    audit_id: UUID,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("read_audit"))
):
    """Diagnóstico de preparación para el cierre formal conforme ISO 19011 §6.6."""
    audit = db.query(Audit).filter(
        Audit.id == audit_id,
        Audit.tenant_id == membership.tenant_id
    ).first()

    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    diagnostics = get_audit_closure_diagnostics(audit_id, membership.tenant_id, db)
    return diagnostics


@router.post("/api/v1/audits/{audit_id}/close", status_code=200)
@router.post("/api/v1/audit-execution/{audit_id}/close", status_code=200)
def close_audit(
    audit_id: UUID,
    body: Optional[AuditCloseInput] = None,
    db: Session = Depends(get_db),
    membership: Membership = Depends(require_perm("manage_findings"))
):
    """Cierra formalmente una auditoría e inmoviliza su expediente."""
    audit = db.query(Audit).filter(
        Audit.id == audit_id,
        Audit.tenant_id == membership.tenant_id
    ).first()

    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")

    if audit.status == "closed":
        return {
            "message": "La auditoría ya se encontraba cerrada formalmente",
            "audit_id": str(audit.id),
            "status": audit.status,
            "closed_at": audit.closed_at.isoformat() if audit.closed_at else None,
            "closed_by_id": str(audit.closed_by_id) if audit.closed_by_id else None,
            "closing_summary": audit.closing_summary
        }

    db.flush()

    diagnostics = get_audit_closure_diagnostics(audit_id, membership.tenant_id, db)
    if not diagnostics["can_close"]:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "message": "No se puede cerrar la auditoría debido a hallazgos o CAPAs pendientes",
                "blockers": diagnostics["blockers"],
                "open_findings_count": diagnostics["open_findings_count"],
                "pending_capas_count": diagnostics["pending_capas_count"]
            }
        )

    summary_text = None
    if body:
        summary_text = body.closing_summary or body.summary
    if not summary_text or len(summary_text.strip()) < 10:
        summary_text = "Cierre formal de auditoría ejecutado satisfactoriamente según dictamen ISO 19011."

    audit.status = "closed"
    audit.closed_at = datetime.now(timezone.utc)
    audit.closed_by_id = membership.user_id
    audit.closing_summary = summary_text.strip()

    db.commit()
    db.refresh(audit)

    return {
        "message": "Auditoría cerrada formalmente exitosa",
        "audit_id": str(audit.id),
        "status": audit.status,
        "closed_at": audit.closed_at.isoformat(),
        "closed_by_id": str(audit.closed_by_id),
        "closing_summary": audit.closing_summary
    }