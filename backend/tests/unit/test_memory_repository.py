from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import backend.models  # noqa: F401 — registers all models
from backend.models.base import Base, utcnow
from backend.repositories.memory import MemoryRepository


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
def repo(session: Session) -> MemoryRepository:
    return MemoryRepository(session)


def test_retrieve_by_role_type_returns_matching(repo: MemoryRepository) -> None:
    repo.create(
        memory_type="role_specific",
        role_type="product_management",
        content_json=json.dumps({"note": "metrics-first works"}),
        confidence=0.8,
    )
    repo.create(
        memory_type="role_specific",
        role_type="consulting",
        content_json=json.dumps({"note": "STAR format works"}),
        confidence=0.9,
    )

    results = repo.retrieve(role_type="product_management")

    assert len(results) == 1
    assert results[0].role_type == "product_management"


def test_retrieve_by_company_returns_matching(repo: MemoryRepository) -> None:
    repo.create(
        memory_type="company_specific",
        company="Accenture",
        content_json=json.dumps({"note": "cost savings emphasis"}),
    )
    repo.create(
        memory_type="company_specific",
        company="Deloitte",
        content_json=json.dumps({"note": "client outcomes"}),
    )

    results = repo.retrieve(company="Accenture")

    assert len(results) == 1
    assert results[0].company == "Accenture"


def test_retrieve_combines_role_and_company(repo: MemoryRepository) -> None:
    repo.create(memory_type="role_specific", role_type="data_analytics", content_json="{}")
    repo.create(memory_type="company_specific", company="Stripe", content_json="{}")

    results = repo.retrieve(role_type="data_analytics", company="Stripe")

    assert len(results) == 2


def test_retrieve_excludes_expired(repo: MemoryRepository) -> None:
    repo.create(
        memory_type="long_term",
        role_type="engineering",
        content_json="{}",
        expires_at="2000-01-01T00:00:00.000000",  # past
    )
    repo.create(
        memory_type="long_term",
        role_type="engineering",
        content_json="{}",
        expires_at=None,  # permanent
    )

    results = repo.retrieve(role_type="engineering")

    assert len(results) == 1
    assert results[0].expires_at is None


def test_retrieve_orders_by_confidence_desc(repo: MemoryRepository) -> None:
    repo.create(memory_type="role_specific", role_type="tpm_solutions", content_json="{}", confidence=0.3)
    repo.create(memory_type="role_specific", role_type="tpm_solutions", content_json="{}", confidence=0.9)
    repo.create(memory_type="role_specific", role_type="tpm_solutions", content_json="{}", confidence=0.6)

    results = repo.retrieve(role_type="tpm_solutions")

    confidences = [r.confidence for r in results]
    assert confidences == [0.9, 0.6, 0.3]


def test_retrieve_no_filters_returns_empty(repo: MemoryRepository) -> None:
    repo.create(memory_type="role_specific", role_type="engineering", content_json="{}")

    assert repo.retrieve() == []


def test_prune_expired_removes_only_expired(repo: MemoryRepository) -> None:
    repo.create(memory_type="long_term", role_type="x", content_json="{}", expires_at="2000-01-01T00:00:00.000000")
    repo.create(memory_type="long_term", role_type="x", content_json="{}", expires_at=None)

    removed = repo.prune_expired()

    assert removed == 1
    assert repo.count() == 1
