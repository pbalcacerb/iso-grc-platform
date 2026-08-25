from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Audit, ChecklistItem, Client, QuestionPack

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AuditCreate(BaseModel):
    client_id: UUID
    standard_id: UUID
    name: str
    status: str = "planned"

class ChecklistUpdate(BaseModel):
    response: str
    notes: str
    status: str

@router.post("/audits")
def create_audit(
    audit: AuditCreate,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    # Get tenant_id from the session cookie
    session = request.cookies.get("session")
    if not session:
        raise HTTPException(status_code=403, detail="Session cookie missing")
    
    # Parse session cookie (format: "tenant_id=<uuid>;user_id=<uuid>")
    tenant_part = next((p for p in session.split(";") if p.startswith("tenant_id=")), None)
    if not tenant_part:
        raise HTTPException(status_code=403, detail="Tenant ID missing in session")
    
    tenant_id = UUID(tenant_part.split("=")[1])

    # Verify client exists
    client = db.query(Client).filter(Client.id == audit.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Create the audit
    db_audit = Audit(
        client_id=audit.client_id,
        standard_id=audit.standard_id,
        name=audit.name,
        status=audit.status,
        tenant_id=tenant_id
    )
    db.add(db_audit)
    db.commit()
    db.refresh(db_audit)

    # Create checklist items from question packs
    question_packs = db.query(QuestionPack).all()
    for qp in question_packs:
        checklist_item = ChecklistItem(
            audit_id=db_audit.id,
            question_pack_id=qp.id,
            status="pending"
        )
        db.add(checklist_item)
    db.commit()

    return {"id": db_audit.id, **audit.model_dump()}

@router.get("/audits/{audit_id}/checklist")
def get_checklist(audit_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    checklist_items = db.query(ChecklistItem).filter(ChecklistItem.audit_id == audit_id).all()
    return [
        {
            "id": item.id,
            "question": item.question_pack.question,
            "expected_evidence": item.question_pack.expected_evidence,
            "response": item.response,
            "notes": item.notes,
            "status": item.status
        }
        for item in checklist_items
    ]

@router.post("/audits/{audit_id}/checklist/{item_id}")
def update_checklist_item(
    audit_id: UUID, item_id: UUID, update: ChecklistUpdate, db: Session = Depends(get_db)
) -> dict:
    checklist_item = db.query(ChecklistItem).filter(
        ChecklistItem.id == item_id,
        ChecklistItem.audit_id == audit_id
    ).first()

    if not checklist_item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    checklist_item.response = update.response
    checklist_item.notes = update.notes
    checklist_item.status = update.status

    db.commit()
    db.refresh(checklist_item)

    return {"message": "Checklist item updated successfully"}