"""Punto de entrada principal - Plataforma ISO GRC."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.db import init_db
from app.logging_config import setup_logging
from app.middleware import RequestLoggingMiddleware
from scripts.seed_demo import seed_demo_data

# 1. Configuración de Logging
setup_logging()
logger = logging.getLogger("iso-grc.main")


# 2. Ciclo de vida de la aplicación (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación: inicialización de BD y datos semilla."""
    try:
        loop = asyncio.get_running_loop()

        # Ejecución DDL de sincronización y creación de tablas
        await loop.run_in_executor(None, init_db)
        logger.info("✅ Base de datos inicializada y esquema sincronizado.")

        # Ejecución idempotente de datos semilla (Demo ISO + Admin)
        await loop.run_in_executor(None, seed_demo_data)
        logger.info("✅ Carga de datos iniciales (Seed) verificada.")

    except Exception as e:
        logger.error(f"❌ Error durante la inicialización de la base de datos: {e}")

    yield


# 3. Inicialización de FastAPI
app = FastAPI(title="ISO GRC Platform", version="0.1.0", lifespan=lifespan)

# 4. Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda r, e: JSONResponse(
        status_code=429, content={"detail": "Rate limit exceeded"}
    ),
)

# 5. Middleware (Registrar antes de los routers)
app.add_middleware(RequestLoggingMiddleware)

# 6. Importación e inclusión de Routers
from app.health import router as health_router
from app.web import router as web_router

app.include_router(health_router)
app.include_router(web_router)

# Inclusión defensiva de routers de módulos de negocio
try:
    from app.audits import router as audits_router

    app.include_router(audits_router)
    logger.info("✅ Router AUDITS incluido.")
except ImportError as e:
    logger.warning(f"⚠️ Router audits no disponible: {e}")

try:
    from app.audit_execution import router as audit_execution_router

    app.include_router(audit_execution_router)
    logger.info("✅ Router AUDIT_EXECUTION incluido.")
except ImportError as e:
    logger.warning(f"⚠️ Router audit_execution no disponible: {e}")

try:
    from app.findings import router as findings_router

    app.include_router(findings_router)
    logger.info("✅ Router FINDINGS incluido.")
except ImportError as e:
    logger.warning(f"⚠️ Router findings no disponible: {e}")

# Verificación de rutas registradas
total_routes = len([r for r in app.routes if hasattr(r, "path")])
logger.info(f"✅ Rutas totales registradas NATIVAMENTE: {total_routes}")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)