from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import backend.models  # noqa: F401 — registers all models
from backend.models.base import Base
from backend.database import get_async_session, get_session
from backend.main import create_app


class _SyncSessionBridge:
    """Test shim for the 12.2 async boundary.

    Production routes depend on ``get_async_session`` (an ``AsyncSession``) and do
    DB work via ``await session.run_sync(fn)``. In tests we hand routes this bridge
    so ``run_sync(fn)`` runs ``fn`` against the existing sync ``test_session`` — so
    API requests and direct-repo tests share one in-memory DB, unchanged.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    async def run_sync(self, fn, *args, **kwargs):
        return fn(self._session, *args, **kwargs)


@pytest.fixture(autouse=True)
def _reset_chroma_manager():
    """Isolate the 12.3 module-level Chroma memo between tests (global state)."""
    from backend.rag.chroma_client import reset_chroma_manager

    reset_chroma_manager()
    yield
    reset_chroma_manager()


@pytest.fixture(autouse=True)
def _reset_recovery_state():
    """Clear the module-global READONLY_RECOVERY flag between tests.

    Some recovery/restore tests set it via a manual enter/clear; if an assertion in
    that window fails, the flag leaks and 503s every later mutating route. Reset here
    so test ordering can't pollute unrelated tests."""
    from backend.recovery import RECOVERY

    RECOVERY.clear()
    yield
    RECOVERY.clear()


def _enable_fk(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def test_engine():
    """In-memory SQLite engine shared across all threads via StaticPool.

    StaticPool ensures a single underlying connection is reused, so the schema
    created by create_all() is visible to sessions opened from any thread
    (including the ASGI thread used by FastAPI TestClient).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _enable_fk)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Database session backed by in-memory SQLite.

    12.14: seed the `default` tenant and bind it on the session so tenant-scoped
    repositories auto-inject/auto-filter to it — existing single-tenant tests stay
    green without per-test changes. Tests exercising the guard or multiple tenants
    override `session.info["tenant_id"]` themselves.
    """
    from backend.services.tenancy import ensure_default_tenant, set_session_tenant

    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSession()
    set_session_tenant(session, ensure_default_tenant(session))
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(test_session) -> Generator[TestClient, None, None]:
    """FastAPI test client with DB dependency overridden and lifespan suppressed.

    The production lifespan calls init_db() and seed_system_config() against
    the module-level engine (bound to the real DB at import time). Suppressing
    it prevents tests from mutating the real SQLite file.
    """

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = create_app()
    app.router.lifespan_context = _noop_lifespan  # type: ignore[assignment]

    def override_get_session():
        try:
            yield test_session
            test_session.commit()
        except Exception:
            test_session.rollback()
            raise

    async def override_get_async_session():
        bridge = _SyncSessionBridge(test_session)
        try:
            yield bridge
            test_session.commit()
        except Exception:
            test_session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_async_session] = override_get_async_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
