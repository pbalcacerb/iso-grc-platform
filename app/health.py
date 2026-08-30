"""Health check para load balancers y monitoreo."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> JSONResponse:
    """Liveness + readiness: responde 200 si la app y la DB están operativas."""
    status = {"status": "ok", "checks": {}, "uptime_seconds": round(time.time() - _start_time, 2)}
    http_status = 200

    # Check de DB
    try:
        db.execute(text("SELECT 1"))
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {e}"
        status["status"] = "degraded"
        http_status = 503

    status["timestamp"] = datetime.now(timezone.utc).isoformat()
    return JSONResponse(content=status, status_code=http_status)


@router.get("/health/live")
def liveness() -> JSONResponse:
    """Liveness puro: solo confirma que el proceso responde."""
    return JSONResponse(content={"status": "alive"})