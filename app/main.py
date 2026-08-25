"""Aplicación principal FastAPI."""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.middleware import SessionMiddleware
from app.auth.register import router as register_router
from app.auth.login import router as login_router
from app.auth.logout import router as logout_router
from app.api.clients import router as clients_router
from app.api.audits import router as audits_router

app = FastAPI(title="ISO GRC Platform", version="0.1.0")

# Middleware para inyección de contexto RLS (si se usara de forma global)
app.add_middleware(SessionMiddleware)

# Routers de autenticación
app.include_router(register_router, prefix="/auth")
app.include_router(login_router, prefix="/auth")
app.include_router(logout_router, prefix="/auth")

# Routers de API (ya tienen prefix="/api" dentro de sus propios archivos)
app.include_router(clients_router)
app.include_router(audits_router)


@app.get("/")
def root():
    """Redirige a la documentación interactiva."""
    return RedirectResponse(url="/docs")