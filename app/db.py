# Database helper functions
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.config import settings
from app.models import Base


def get_db() -> Session:
    """Returns a new database session."""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    db = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    return db()

def get_session_with_rls(tenant_id: UUID | None = None, user_id: UUID | None = None) -> Session:
    """
    Create a new session with Row-Level Security (RLS) context.
    Sets `app.current_tenant_id` and `app.current_user_id` if provided.
    """
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)  # Ensure tables are created
    session = Session(bind=engine)
    
    # Set RLS context for the session
    if tenant_id is not None:
        session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)}
        )
    if user_id is not None:
        session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)}
        )
    
    return session

import functools
from contextlib import contextmanager
from typing import Any

# Configuración del engine basada en settings
engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(engine)  # Ensure tables are created
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

@contextmanager
def transaction(tenant_id: UUID | str | None = None, user_id: UUID | str | None = None) -> Any:
    """
    Helper de transacción que ejecuta SET LOCAL para tenant_id y user_id.
    Los valores se derivan del contexto autenticado y nunca del input directo.
    """
    db = SessionLocal()
    try:
        if tenant_id is not None:
            db.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)},
            )
        if user_id is not None:
            db.execute(
                text("SET LOCAL app.current_user_id = :user_id"),
                {"user_id": str(user_id)},
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