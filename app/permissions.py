"""Matriz de permisos por rol (WP2.5)."""
from fastapi import Depends, HTTPException

from app.models import Membership
from app.security import get_membership

PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "manage_users", "create_client", "create_audit", "upload_evidence",
        "approve_item", "reopen_item", "view_internal", "manage_findings",
        "approve_report", "view_portal",
    },
    "auditor": {
        "create_client", "create_audit", "upload_evidence", "reopen_item",
        "view_internal", "manage_findings",
    },
    "reviewer": {
        "approve_item", "reopen_item", "view_internal", "manage_findings",
        "approve_report",
    },
    "client_editor": {"upload_evidence", "view_portal", "propose_capa"},
    "client_viewer": {"view_portal"},
    "viewer": {"view_portal"},
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