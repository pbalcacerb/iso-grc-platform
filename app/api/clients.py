"""Endpoints de clientes con aislamiento por tenant."""
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


@router.post("/clients")
def create_client(
    client: ClientCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    tenant_id = _get_tenant_from_cookie(request)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_client = Client(
        tenant_id=tenant_id,
        name=client.name,
        sector=client.sector,
        country=client.country,
        confidentiality_level=client.confidentiality_level,
        status="active",
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return {"id": str(db_client.id), **client.model_dump()}


@router.get("/clients")
def list_clients(
    request: Request,
    db: Session = Depends(get_db),
) -> list[dict]:
    tenant_id = _get_tenant_from_cookie(request)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    clients = db.query(Client).filter(Client.tenant_id == tenant_id).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "sector": c.sector,
            "country": c.country,
            "confidentiality_level": c.confidentiality_level,
            "status": c.status,
        }
        for c in clients
    ]