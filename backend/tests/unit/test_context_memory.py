from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import backend.models  # noqa: F401
from backend.models.base import Base
from backend.services.intelligence.context_memory import ContextMemory


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = SessionLocal()
    from backend.services.tenancy import ensure_default_tenant, set_session_tenant
    set_session_tenant(s, ensure_default_tenant(s))
    yield s
    s.close()


@pytest.fixture
def memory(session: Session) -> ContextMemory:
    return ContextMemory(session)


def test_record_then_retrieve_roundtrip(memory: ContextMemory) -> None:
    memory.record(
        memory_type="role_specific",
        role_type="product_management",
        content={"insight": "metrics-first bullets win"},
        confidence=0.8,
    )

    results = memory.retrieve(role_type="product_management")

    assert len(results) == 1
    assert results[0]["insight"] == "metrics-first bullets win"


def test_retrieve_unknown_role_returns_empty(memory: ContextMemory) -> None:
    assert memory.retrieve(role_type="nonexistent") == []


def test_format_for_injection_renders_memory_block(memory: ContextMemory) -> None:
    memory.record(
        memory_type="company_specific",
        company="Accenture",
        content={"insight": "emphasize cost savings"},
        confidence=0.9,
    )

    block = memory.format_for_injection(company="Accenture")

    assert "[MEMORY:" in block
    assert "emphasize cost savings" in block


def test_format_for_injection_empty_when_no_memories(memory: ContextMemory) -> None:
    assert memory.format_for_injection(role_type="engineering") == ""


def test_record_outcome_persists_long_term(memory: ContextMemory) -> None:
    memory.record_outcome(
        role_type="consulting",
        company="Deloitte",
        content={"outcome": "interview", "bullets_used": ["e1", "e2"]},
    )

    results = memory.retrieve(role_type="consulting", company="Deloitte")

    assert len(results) == 1
    assert results[0]["outcome"] == "interview"
