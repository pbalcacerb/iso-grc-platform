"""Aplicación principal FastAPI."""
from fastapi import FastAPI

from app.api.audits import router as audits_router
from app.api.clients import router as clients_router
from app.api.evidence import router as evidence_router
from app.auth.login import router as login_router
from app.auth.logout import router as logout_router
from app.auth.register import router as register_router
from app.middleware import SessionMiddleware
from app.web import router as web_router

app = FastAPI(title="ISO GRC Platform", version="0.1.0")

app.add_middleware(SessionMiddleware)

app.include_router(web_router)
app.include_router(register_router, prefix="/auth")
app.include_router(login_router, prefix="/auth")
app.include_router(logout_router, prefix="/auth")
app.include_router(clients_router)
app.include_router(audits_router)
app.include_router(evidence_router)