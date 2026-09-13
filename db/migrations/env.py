"""Entorno Alembic: sincronizado automáticamente con app.config y app.models."""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Registrar el directorio raíz en sys.path para habilitar la importación de app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Vincula los modelos de SQLAlchemy para detección automática de cambios (--autogenerate)
target_metadata = Base.metadata

# Resuelve la conexión usando la variable de entorno o fallback a settings.DATABASE_URL
database_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo online conectando a la base de datos."""
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()