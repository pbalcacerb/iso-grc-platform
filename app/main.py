"""Aplicación principal FastAPI."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.audits import router as audits_router
from app.api.clients import router as clients_router
from app.api.evidence import router as evidence_router
from app.auth.login import router as login_router
from app.auth.logout import router as logout_router
from app.auth.register import router as register_router
from app.health import router as health_router
from app.middleware import RequestLoggingMiddleware, setup_json_logging
from app.web import router as web_router

# 1. Configurar logging estructurado
setup_json_logging()

# 2. Configurar Rate Limiter Global
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Maneja los eventos de inicio y cierre de la aplicación (Lifespan)."""
    from app.db import engine
    from app.models import Base

    # Crear tablas idempotentes al iniciar
    Base.metadata.create_all(bind=engine)
    
    yield


app = FastAPI(
    title="ISO GRC Platform",
    version="0.1.0",
    lifespan=lifespan
)

# 3. Estado y Manejador de Excepciones para Rate Limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 4. Registro de Middlewares (Orden Correcto: de afuera hacia adentro)
# Primero se ejecuta RequestLoggingMiddleware y luego SlowAPIMiddleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)

# 5. Routers de Sistema y Web
app.include_router(health_router)
app.include_router(web_router)

# 6. Routers de Autenticación (API)
app.include_router(register_router, prefix="/auth")
app.include_router(login_router, prefix="/auth")
app.include_router(logout_router, prefix="/auth")

# 7. Routers de Negocio (API)
app.include_router(clients_router)
app.include_router(audits_router)
app.include_router(evidence_router)