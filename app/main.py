"""Punto de entrada principal - Resolución Definitiva."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# 1. Logging
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("iso-grc.main")

# 2. DB & Models
from app.db import engine
from app.models import Base
from scripts.seed_demo import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación: inicialización de BD y datos semilla."""
    try:
        loop = asyncio.get_running_loop()

        # 1. Creación síncrona de tablas en executor asíncrono nativo
        await loop.run_in_executor(None, Base.metadata.create_all, engine)
        logger.info("✅ Tablas de la base de datos verificadas/creadas.")

        # 2. Ejecución idempotente de datos semilla (Demo ISO + Admin)
        await loop.run_in_executor(None, seed_demo_data)
        logger.info("✅ Carga de datos iniciales (Seed) verificada.")

    except Exception as e:
        logger.error(f"❌ Error durante la inicialización de la base de datos: {e}")
        # En entornos críticos, considera relanzar la excepción para detener el arranque si falla la BD:
        # raise e

    yield


# 3. Inicialización de la App
app = FastAPI(title="ISO GRC Platform", version="0.1.0", lifespan=lifespan)

# 4. Rate Limiter y Excepciones
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda r, e: JSONResponse(
        status_code=429, content={"detail": "Rate limit exceeded"}
    ),
)

# 5. Middlewares (Registrar ANTES de los routers)
from app.middleware import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)

# 6. Importación y Registro de Routers
from app.health import router as health_router
from app.web import router as web_router

app.include_router(health_router)
app.include_router(web_router)

# Flattening explicito de sub-rutas para asegurar visibilidad directa en app.routes
for sub_router in [health_router, web_router]:
    for route in sub_router.routes:
        if route not in app.router.routes:
            app.router.routes.append(route)

total_routes = len([r for r in app.routes if hasattr(r, "path")])
logger.info(f"✅ Rutas totales registradas NATIVAMENTE: {total_routes}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)