"""Alembic environment configuration."""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Add project root to Python path so we can import app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401  register all models with Base.metadata
from app.config import settings
from app.database import Base, normalize_database_url

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata
db_url = normalize_database_url(
    settings.database_url or config.get_main_option("sqlalchemy.url")
)


def run_migrations_offline():
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode with async engine."""

    def do_run_migrations(connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # One transaction per revision. Alembic's default is a single
            # transaction for the whole run, which breaks a revision that adds
            # a value to an enum and then uses that value: PostgreSQL refuses
            # to use a value in the transaction that added it. See
            # docs/agent-instructions/data-model.md.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    async def run_async() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    import asyncio

    asyncio.run(run_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
