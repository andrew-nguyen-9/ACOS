import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Make sure `backend` package is importable when Alembic runs from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import all models so their metadata is registered
import backend.models  # noqa: F401
from backend.models.base import Base
from backend.config import get_settings

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: running migrations in-process (e.g. the
    # roundtrip test) must not silence the app's already-configured loggers.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment/config
config.set_main_option("sqlalchemy.url", get_settings().db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    from backend.database import _to_async_url

    url = config.get_main_option("sqlalchemy.url")
    assert url is not None  # set at module load from get_settings().db_url
    connectable = create_async_engine(_to_async_url(url), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_migrations_online_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
