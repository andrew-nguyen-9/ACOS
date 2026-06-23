"""Phase 12.2 — exercise the REAL async boundary (not the conftest sync bridge).

The default `client` fixture swaps `get_async_session` for a sync-session shim, so
the wider suite proves the sync `_impl` logic but never the actual AsyncSession
commit/rollback over aiosqlite. These tests bind the real `AsyncSessionLocal` to a
temp-file aiosqlite engine and drive it through `get_async_session` directly and
through an ASGI request, covering: persist-on-success, rollback-on-exception, the
full route stack, and the restore-path pool dispose.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text

import backend.models  # noqa: F401 — register models
from backend import database as db
from backend.models.base import Base
from backend.models.system_config import SystemConfig
from backend.main import create_app


@pytest_asyncio.fixture
async def async_db(tmp_path, monkeypatch):
    """Real aiosqlite engine on a temp file, wired into the module's AsyncSessionLocal."""
    engine = db.build_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'async.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(db, "AsyncSessionLocal", maker)
    yield engine
    await engine.dispose()


async def test_boundary_commits_on_success(async_db):
    """A flush inside run_sync is persisted by the dependency's boundary commit."""
    agen = db.get_async_session()
    session = await agen.__anext__()
    await session.run_sync(
        lambda s: (s.add(SystemConfig(key="k_ok", value="v")), s.flush())
    )
    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()  # runs the commit + close branch

    async with db.AsyncSessionLocal() as verify:
        got = await verify.run_sync(lambda s: s.get(SystemConfig, "k_ok"))
        assert got is not None and got.value == "v"


async def test_boundary_rolls_back_on_exception(async_db):
    """An exception after a flush rolls the write back — no partial persist."""
    agen = db.get_async_session()
    session = await agen.__anext__()
    await session.run_sync(
        lambda s: (s.add(SystemConfig(key="k_bad", value="v")), s.flush())
    )
    with pytest.raises(RuntimeError):
        await agen.athrow(RuntimeError("boom"))  # triggers the rollback branch

    async with db.AsyncSessionLocal() as verify:
        got = await verify.run_sync(lambda s: s.get(SystemConfig, "k_bad"))
        assert got is None


async def test_async_route_persists_through_real_stack(async_db):
    """End-to-end: POST then GET an application through the real async route stack."""

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app = create_app()
    app.router.lifespan_context = _noop_lifespan  # type: ignore[assignment]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post(
            "/api/v1/applications", json={"company": "Acme", "position": "PM"}
        )
        assert created.status_code == 201
        app_id = created.json()["id"]

        # A second request = a fresh session/transaction; only a real boundary
        # commit makes the row visible here.
        fetched = await ac.get(f"/api/v1/applications/{app_id}")
        assert fetched.status_code == 200
        assert fetched.json()["company"] == "Acme"


async def test_async_pool_dispose_then_reusable(async_db):
    """The restore-path dispose (async_engine.sync_engine.dispose) drops aiosqlite
    handles synchronously and the engine reconnects cleanly afterward."""
    async with async_db.connect() as conn:
        assert (await conn.exec_driver_sql("SELECT 1")).scalar() == 1

    # The exact call backup.restore_snapshot / reset_engine make before a file swap.
    async_db.sync_engine.dispose()

    async with async_db.connect() as conn:
        assert (await conn.execute(text("SELECT 1"))).scalar() == 1
