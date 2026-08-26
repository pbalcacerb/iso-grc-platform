"""Endpoints de clientes con tenant derivado de la sesión."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client

router = APIRouter(prefix="/api", tags=["clients"])


class ClientCreate(BaseModel):
    name: str
    sector: str = ""
    country: str = ""
    confidentiality_level: str = "internal"


def tenant_from_request(request: Request) -> uuid.UUID:
    cookie = request.cookies.get("session") or ""
    m = re.search(r"tenant=([0-9a-f\-]{36})", cookie)
    if not m:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(m.group(1))


@router.post("/clients")
def create_client(
    client: ClientCreate, request: Request, db: Session = Depends(get_db),
) -> dict:
    tenant_id = tenant_from_request(request)
    obj = Client(tenant_id=tenant_id, **client.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": str(obj.id), **client.model_dump()}


@router.get("/clients")
def list_clients(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    tenant_id = tenant_from_request(request)
    rows = db.query(Client).filter(Client.tenant_id == tenant_id).all()
    return [
        {"id": str(c.id), "name": c.name, "sector": c.sector,
         "country": c.country,
         "confidentiality_level": c.confidentiality_level, "status": c.status}
        for c in rows
    ]