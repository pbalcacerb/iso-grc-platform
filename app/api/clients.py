from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client

router = APIRouter()

class ClientCreate(BaseModel):
    name: str
    sector: str = ""
    country: str = ""
    confidentiality_level: str = "internal"

@router.post("/clients")
def create_client(
    client: ClientCreate,
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

    # Create the client
    db_client = Client(
        name=client.name,
        sector=client.sector,
        country=client.country,
        confidentiality_level=client.confidentiality_level,
        tenant_id=tenant_id
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    return {"id": db_client.id, **client.model_dump()}

@router.get("/clients")
def list_clients(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    # Get tenant_id from the session cookie
    session = request.cookies.get("session")
    if not session:
        return []
    
    # Parse session cookie (format: "tenant_id=<uuid>;user_id=<uuid>")
    tenant_part = next((p for p in session.split(";") if p.startswith("tenant_id=")), None)
    if not tenant_part:
        return []
    
    tenant_id = UUID(tenant_part.split("=")[1])

    clients = db.query(Client).filter(Client.tenant_id == tenant_id).all()
    return [
        {
            "id": client.id,
            "name": client.name,
            "sector": client.sector,
            "country": client.country,
            "confidentiality_level": client.confidentiality_level
        }
        for client in clients
    ]