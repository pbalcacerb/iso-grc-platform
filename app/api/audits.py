"""Endpoints de auditorías y checklist."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Audit, ChecklistItem, QuestionPack, Clause

router = APIRouter(prefix="/api", tags=["audits"])


class AuditCreate(BaseModel):
    client_id: uuid.UUID
    standard_id: uuid.UUID
    name: str
    status: str = "planned"


class ChecklistUpdate(BaseModel):
    response: str = ""
    notes: str = ""
    status: str = "pending"


def _get_tenant_from_cookie(request: Request) -> uuid.UUID | None:
    session = request.cookies.get("session")
    if not session:
        return None
    match = re.search(r"tenant=([a-f0-9\-]{36})", session)
    if match:
        try:
            return uuid.UUID(match.group(1))
        except ValueError:
            return None
    return None


@router.post("/audits")
def create_audit(
    audit: AuditCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    tenant_id = _get_tenant_from_cookie(request)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_audit = Audit(
        tenant_id=tenant_id,
        client_id=audit.client_id,
        standard_id=audit.standard_id,
        name=audit.name,
        status=audit.status,
    )
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)

    # Crear checklist items automáticamente desde question_packs
    clauses = db.query(Clause).filter(Clause.standard_id == audit.standard_id).all()
    for clause in clauses:
        packs = db.query(QuestionPack).filter(QuestionPack.clause_id == clause.id).all()
        for pack in packs:
            item = ChecklistItem(
                tenant_id=tenant_id,
                audit_id=db_audit.id,
                clause_id=clause.id,
                question_pack_id=pack.id,
                status="pending",
            )
            db.add(item)
    db.commit()

    return {
        "id": str(db_audit.id),
        "client_id": str(audit.client_id),
        "standard_id": str(audit.standard_id),
        "name": audit.name,
        "status": audit.status,
    }


@router.get("/audits/{audit_id}/checklist")
def get_checklist(
    audit_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> list[dict]:
    tenant_id = _get_tenant_from_cookie(request)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    items = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.audit_id == audit_id, ChecklistItem.tenant_id == tenant_id)
        .all()
    )
    return [
        {
            "id": str(i.id),
            "audit_id": str(i.audit_id),
            "clause_id": str(i.clause_id),
            "question_pack_id": str(i.question_pack_id),
            "status": i.status,
            "response": i.response,
            "notes": i.notes,
        }
        for i in items
    ]


@router.post("/audits/{audit_id}/checklist/{item_id}")
def update_checklist_item(
    audit_id: uuid.UUID,
    item_id: uuid.UUID,
    update: ChecklistUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    tenant_id = _get_tenant_from_cookie(request)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    item = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.id == item_id, ChecklistItem.tenant_id == tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    item.response = update.response
    item.notes = update.notes
    item.status = update.status
    db.commit()
    db.refresh(item)

    return {
        "id": str(item.id),
        "status": item.status,
        "response": item.response,
        "notes": item.notes,
    }