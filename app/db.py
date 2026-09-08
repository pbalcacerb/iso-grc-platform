"""Helper de base de datos con UUID y contexto RLS."""
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# En db.py
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session_with_rls(tenant_id: uuid.UUID | None, user_id: uuid.UUID | None) -> Iterator[Session]:
    """Abre una sesión y establece el contexto RLS."""
    with Session(engine) as session:
        if tenant_id:
            session.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tenant_id)})
        if user_id:
            session.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(user_id)})
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise