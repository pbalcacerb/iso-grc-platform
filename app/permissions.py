"""Matriz de permisos por rol (WP2.5-3.5, modelo de 8 roles)."""
from fastapi import Depends, HTTPException

from app.models import Membership
from app.security import get_membership

PERMISSIONS: dict[str, set[str]] = {
    # ===== EQUIPO AUDITOR (propietario de la plataforma) =====
    "owner": {
        "manage_users", "manage_platform",
        "create_client", "create_audit", "manage_schedule",
        "upload_evidence", "evaluate_evidence",
        "draft_findings", "classify_findings",
        "approve_item", "reopen_item",
        "view_internal", "manage_findings", "approve_report",
        "view_portal",
    },
    "lead_auditor": {
        "create_client", "create_audit", "manage_schedule",
        "upload_evidence", "evaluate_evidence",
        "draft_findings", "classify_findings",
        "approve_item", "reopen_item",
        "view_internal", "manage_findings", "approve_report",
    },
    "auditor": {
        "create_audit", "manage_schedule",
        "upload_evidence", "evaluate_evidence",
        "draft_findings", "reopen_item",
        "view_internal", "manage_findings",
    },
    "coordinator": {  # Revisor: trazabilidad y agenda, edición limitada (NO aprueba)
        "manage_schedule", "reopen_item", "view_internal",
    },
    "observer": {  # Experto técnico + auditor en formación
        "view_dashboard",
        "view_portal",
        "upload_evidence",
        "comment",
        },

    # ===== ORGANIZACIÓN AUDITADA (cliente) =====
    "client_responsible": {  # Líder ISO / Responsable
        "upload_evidence", "view_portal", "view_findings",
        "propose_capa", "confirm_interviews",
    },
    "client_process_owner": {  # Dueños de proceso
        "upload_evidence", "view_portal",
    },
    "client_sponsor": {  # Alta Dirección
        "view_portal", "view_findings", "approve_capa_commitment",
    },
}


def role_can(role: str | None, permission: str) -> bool:
    return permission in PERMISSIONS.get(role or "", set())


def require_perm(permission: str):
    """Dependencia FastAPI: 403 si el rol no tiene el permiso."""
    def dependency(membership: Membership = Depends(get_membership)) -> Membership:
        if not role_can(membership.role, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return membership
    return dependency