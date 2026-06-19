from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import backend.models  # noqa: F401 — registers all models
from backend.models.base import Base
from backend.database import get_session, build_engine
from backend.main import create_app


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
def test_session(test_engine) -> Session:
    """Database session backed by in-memory SQLite."""
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(test_session) -> TestClient:
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

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
