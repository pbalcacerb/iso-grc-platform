"""Endpoints de auditorías y checklist con tenant de la sesión."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Audit, ChecklistItem, Clause, QuestionPack

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


def tenant_from_request(request: Request) -> uuid.UUID:
    cookie = request.cookies.get("session") or ""
    m = re.search(r"tenant=([0-9a-f\-]{36})", cookie)
    if not m:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(m.group(1))


@router.post("/audits")
def create_audit(
    audit: AuditCreate, request: Request, db: Session = Depends(get_db),
) -> dict:
    tenant_id = tenant_from_request(request)
    obj = Audit(
        tenant_id=tenant_id, client_id=audit.client_id,
        standard_id=audit.standard_id, name=audit.name, status=audit.status,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    pairs = db.query(Clause.id, QuestionPack.id).join(
        QuestionPack, QuestionPack.clause_id == Clause.id,
    ).filter(Clause.standard_id == audit.standard_id).all()
    for clause_id, pack_id in pairs:
        db.add(ChecklistItem(
            tenant_id=tenant_id, audit_id=obj.id,
            clause_id=clause_id, question_pack_id=pack_id,
        ))
    db.commit()
    return {"id": str(obj.id), "name": obj.name, "status": obj.status}


@router.get("/audits/{audit_id}/checklist")
def get_checklist(
    audit_id: uuid.UUID, request: Request, db: Session = Depends(get_db),
) -> list[dict]:
    tenant_id = tenant_from_request(request)
    rows = db.query(ChecklistItem).filter(
        ChecklistItem.audit_id == audit_id,
        ChecklistItem.tenant_id == tenant_id,
    ).all()
    return [
        {"id": str(i.id), "status": i.status, "response": i.response,
         "notes": i.notes}
        for i in rows
    ]


@router.post("/audits/{audit_id}/checklist/{item_id}")
def update_checklist_item(
    audit_id: uuid.UUID, item_id: uuid.UUID, update: ChecklistUpdate,
    request: Request, db: Session = Depends(get_db),
) -> dict:
    tenant_id = tenant_from_request(request)
    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == item_id, ChecklistItem.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    item.response = update.response
    item.notes = update.notes
    item.status = update.status
    db.commit()
    return {"id": str(item.id), "status": item.status}