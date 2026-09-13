"""Helper de base de datos con UUID, contexto RLS y sincronización de esquema."""
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema_sync():
    """Garantiza la existencia de columnas y corrige restricciones FK en PostgreSQL."""
    try:
        with engine.connect() as conn:
            # 1. Asegurar columna severity
            conn.execute(
                text(
                    "ALTER TABLE findings ADD COLUMN IF NOT EXISTS severity VARCHAR(50) DEFAULT 'MINOR' NOT NULL;"
                )
            )
            # 2. Re-apuntar la restricción Foreign Key a audit_checklist_items(id)
            conn.execute(
                text(
                    "ALTER TABLE findings DROP CONSTRAINT IF EXISTS findings_checklist_item_id_fkey;"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE findings ADD CONSTRAINT findings_checklist_item_id_fkey "
                    "FOREIGN KEY (checklist_item_id) REFERENCES audit_checklist_items(id) ON DELETE CASCADE;"
                )
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️ Aviso en sincronización de esquema: {e}")


def init_db():
    """Ejecuta migraciones DDL directas de parcheo y crea tablas faltantes."""
    ensure_schema_sync()
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para inyección de sesión en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_with_rls(
    tenant_id: uuid.UUID | None, user_id: uuid.UUID | None
) -> Iterator[Session]:
    """Abre una sesión y establece el contexto RLS."""
    with Session(engine) as session:
        if tenant_id:
            session.execute(
                text("SELECT set_config('app.current_tenant_id', :t, true)"),
                {"t": str(tenant_id)},
            )
        if user_id:
            session.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(user_id)},
            )
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise