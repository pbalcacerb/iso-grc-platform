"""Aplicación principal FastAPI."""
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
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

# Configurar logging JSON estructurado (WP3)
setup_json_logging()

# Rate limiter global (WP3)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(title="ISO GRC Platform", version="0.1.0")

# Middleware de logging de requests (WP3)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers de salud y web
app.include_router(health_router)
app.include_router(web_router)

# Routers de autenticación (API)
app.include_router(register_router, prefix="/auth")
app.include_router(login_router, prefix="/auth")
app.include_router(logout_router, prefix="/auth")

# Routers de negocio (API)
app.include_router(clients_router)
app.include_router(audits_router)
app.include_router(evidence_router)