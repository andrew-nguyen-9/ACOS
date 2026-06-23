"""Phase 12.2 — async engine/session foundation.

Verifies the aiosqlite async engine reuses the 12.1 hot-path pragmas and that
the ``get_async_session`` dependency yields an ``AsyncSession`` and tears down
cleanly (commit on success path, close on exit).
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend import database as db


async def test_async_engine_applies_hotpath_pragmas(tmp_path):
    """Pragmas from 12.1 (_apply_pragmas) read back on the async connection."""
    engine = db.build_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'pragma.db'}")
    try:
        async with engine.connect() as conn:
            journal = (await conn.exec_driver_sql("PRAGMA journal_mode")).scalar()
            synchronous = (await conn.exec_driver_sql("PRAGMA synchronous")).scalar()
            mmap = (await conn.exec_driver_sql("PRAGMA mmap_size")).scalar()
            fk = (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar()
    finally:
        await engine.dispose()

    assert journal == "wal"
    assert synchronous == 1  # NORMAL, safe under WAL
    assert mmap == 268435456  # 256 MiB
    assert fk == 1


async def test_get_async_session_yields_asyncsession_and_closes(tmp_path, monkeypatch):
    """The FastAPI dependency yields an AsyncSession and finalizes cleanly."""
    engine = db.build_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'session.db'}")
    monkeypatch.setattr(
        db, "AsyncSessionLocal", async_sessionmaker(bind=engine, expire_on_commit=False)
    )

    agen = db.get_async_session()
    session = await agen.__anext__()
    assert isinstance(session, AsyncSession)

    value = (await session.execute(text("SELECT 1"))).scalar_one()
    assert value == 1

    # Exhausting the generator runs the commit + close branch without error.
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    await engine.dispose()
