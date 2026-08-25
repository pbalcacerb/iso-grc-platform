import functools
from contextlib import contextmanager
from typing import Any

from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Configuración del engine basada en settings
engine = create_engine(settings.DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

@contextmanager
def transaction(tenant_id: str | None = None, user_id: str | None = None) -> Any:
    """
    Helper de transacción que ejecuta SET LOCAL para tenant_id y user_id.
    Los valores se derivan del contexto autenticado y nunca del input directo.
    """
    db = SessionLocal()
    try:
        if tenant_id is not None:
            db.execute(
                "SET LOCAL app.current_tenant_id = :tenant_id",
                {"tenant_id": tenant_id},
            )
        if user_id is not None:
            db.execute(
                "SET LOCAL app.current_user_id = :user_id",
                {"user_id": user_id},
            )
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def with_session(f):
    """Decorador para manejar sesiones de DB en funciones."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        with transaction() as db:
            kwargs["db"] = db
            return f(*args, **kwargs)
    return wrapped