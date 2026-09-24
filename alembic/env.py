"""Alembic configuration for the service database."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.adapters.persistence.postgresql.tables import metadata
from app.config.settings import settings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
