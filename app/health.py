"""Endpoint de health check para monitoreo."""
from fastapi import APIRouter
from sqlalchemy import text

from app.db import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Verifica conectividad con la base de datos."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}