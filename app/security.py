"""Helpers de seguridad: sesión y permisos por rol."""
import re
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Membership


def parse_session(request: Request) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    cookie = request.cookies.get("session") or ""
    m_t = re.search(r"tenant=([0-9a-f\-]{36})", cookie)
    m_u = re.search(r"user=([0-9a-f\-]{36})", cookie)
    tenant = uuid.UUID(m_t.group(1)) if m_t else None
    user = uuid.UUID(m_u.group(1)) if m_u else None
    return tenant, user


def get_membership(
    request: Request, db: Session = Depends(get_db)
) -> Membership:
    tenant_id, user_id = parse_session(request)
    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == tenant_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return membership


def require_role(*roles: str):
    """Dependencia de FastAPI: 403 si el rol no está permitido."""
    def dependency(membership: Membership = Depends(get_membership)) -> Membership:
        if membership.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return membership
    return dependency