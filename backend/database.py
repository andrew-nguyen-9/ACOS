from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — registers all models with Base.metadata
from backend.models.base import Base
from backend.config import get_settings


def _apply_pragmas(dbapi_connection: object, _: object) -> None:
    """Apply the SQLite hot-path pragmas on every new connection.

    ``journal_mode=WAL`` is persistent (recorded in the DB file header), so a
    re-assert is a cheap no-op. ``synchronous``, ``mmap_size``, and
    ``foreign_keys`` are per-connection and reset to their defaults on each new
    connection, so they must be re-applied here. Registered on the SQLAlchemy
    ``connect`` event; reused by the async engine in 12.2.

    ponytail: these three are the known wins; add cache_size only if a bench shows need.
    """
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")  # safe under WAL (see database/README.md)
    cursor.execute("PRAGMA mmap_size=268435456")  # 256 MiB memory-mapped I/O
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(db_url: str | None = None) -> Engine:
    url = db_url or get_settings().db_url
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=get_settings().debug,
    )
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def _to_async_url(url: str) -> str:
    """Map a sync SQLite URL to its aiosqlite (async) equivalent."""
    if url.startswith("sqlite+aiosqlite:"):
        return url
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    return url


def build_async_engine(db_url: str | None = None) -> AsyncEngine:
    """Async engine over aiosqlite. Reuses 12.1 ``_apply_pragmas`` via the
    underlying ``sync_engine`` connect event (sync DBAPI handler is adapted)."""
    url = _to_async_url(db_url or get_settings().db_url)
    engine = create_async_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=get_settings().debug,
    )
    event.listen(engine.sync_engine, "connect", _apply_pragmas)
    return engine


# Module-level engine and session factory (replaced in tests via conftest)
engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Async engine + session factory (12.2). expire_on_commit=False keeps attributes
# usable after commit without an awaitable refresh — required in async request paths.
async_engine = build_async_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False
)


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if tables exist)."""
    Base.metadata.create_all(bind=engine)


def reset_engine() -> None:
    """Dispose the pooled connections and rebuild the engine + session factory.

    Required around a restore: the live engine's pool holds open handles to the
    SQLite file, so swapping the file underneath them would leave callers reading
    the old (unlinked) inode. Drop the pool, swap, then rebuild against the new file.
    """
    global engine, SessionLocal, async_engine, AsyncSessionLocal
    engine.dispose()
    # Drop the async pool too: it holds aiosqlite handles to the same file, so a
    # restore swap would otherwise leave async request paths on the stale inode.
    # sync_engine.dispose() closes the adapted DBAPI connections synchronously.
    async_engine.sync_engine.dispose()
    engine = build_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    async_engine = build_async_engine()
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, autoflush=False
    )


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session per request (12.2)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def seed_system_config(session: Session) -> None:
    """Insert default system_config rows if they don't exist."""
    from backend.models.system_config import SystemConfig

    defaults = [
        ("default_model", "qwen3:8b", "Default Ollama model for generation"),
        ("embedding_model", "nomic-embed-text", "Ollama model for embeddings"),
        ("embedding_schema_version", "1", "Embedding scheme version; bump on re-embed"),
        ("learning_trigger_count", "5", "Applications before learning refresh"),
        ("retention_floor_fraction", "0.25", "Retention: permanent floor as fraction of success_score"),
        ("retention_decay_days", "180", "Retention: recency exponential decay time constant (days)"),
        ("anchor_percentile", "0.75", "Success anchoring: percentile cutoff for anchor strategies"),
        ("anchor_max_count", "3", "Success anchoring: max anchors merged into candidates"),
        ("ats_keyword_weight", "0.35", "ATS scoring: keyword match weight"),
        ("ats_skill_weight", "0.25", "ATS scoring: skill match weight"),
        ("ats_experience_weight", "0.20", "ATS scoring: experience match weight"),
        ("ats_industry_weight", "0.10", "ATS scoring: industry match weight"),
        ("ats_education_weight", "0.10", "ATS scoring: education match weight"),
        ("github_username", "", "GitHub username for profile integration"),
        ("onboarding_complete", "false", "Whether the first-run wizard has been completed"),
    ]
    for key, value, description in defaults:
        exists = session.get(SystemConfig, key)
        if not exists:
            session.add(SystemConfig(key=key, value=value, description=description))
    session.commit()
