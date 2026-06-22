"""FTS5 lexical search leg (Phase 12.7).

Native SQLite FTS5 BM25 replaces the Python rank_bm25 leg. These tests exercise
the standalone, app-maintained ``documents_fts`` virtual table: search ranking,
doc_type partitioning, upsert/delete sync, and FTS5-query sanitization.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.rag import lexical


@pytest.fixture()
def fts_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = TestSession()
    lexical.ensure_fts5(session)
    yield session
    session.close()
    engine.dispose()


def _seed(session: Session) -> None:
    lexical.upsert(session, "d1", "python async event loop performance tuning", "acos_experiences")
    lexical.upsert(session, "d2", "react frontend component design system", "acos_projects")
    lexical.upsert(session, "d3", "python data pipeline batch embedding throughput", "acos_experiences")
    session.commit()


def test_fts5_available(fts_session):
    assert lexical.fts5_available(fts_session) is True


def test_create_all_builds_documents_fts():
    """The app bootstraps schema via Base.metadata.create_all (not alembic at
    runtime), so the virtual table must be created by an after_create DDL hook —
    otherwise the indexer's lexical sync hits 'no such table' in production."""
    import backend.models  # noqa: F401 — registers models + the FTS5 DDL hook
    from backend.models.base import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        lexical.upsert(session, "x1", "kubernetes orchestration", "acos_experiences")
        session.commit()
        assert [r["id"] for r in lexical.search(session, "kubernetes", ["acos_experiences"], 5)] == ["x1"]
    finally:
        session.close()
        engine.dispose()


def test_search_returns_bm25_ranked_ids(fts_session):
    _seed(fts_session)
    results = lexical.search(fts_session, "python performance tuning", ["acos_experiences"], k=5)
    ids = [r["id"] for r in results]
    assert ids, "expected at least one match"
    # d1 ("python ... performance tuning") is the strongest lexical match.
    assert ids[0] == "d1"
    assert all(r["lexical_score"] >= 0.0 for r in results)


def test_search_filters_by_doc_type(fts_session):
    _seed(fts_session)
    results = lexical.search(fts_session, "design python react", ["acos_projects"], k=5)
    ids = {r["id"] for r in results}
    assert ids == {"d2"}, f"doc_type filter leaked partitions: {ids}"


def test_search_empty_query_returns_empty(fts_session):
    _seed(fts_session)
    assert lexical.search(fts_session, "   ", ["acos_experiences"], k=5) == []


def test_search_no_doc_types_returns_empty(fts_session):
    _seed(fts_session)
    assert lexical.search(fts_session, "python", [], k=5) == []


def test_upsert_updates_existing_row(fts_session):
    lexical.upsert(fts_session, "d1", "kubernetes orchestration", "acos_experiences")
    fts_session.commit()
    assert lexical.search(fts_session, "kubernetes", ["acos_experiences"], k=5)
    # Re-upsert same id with new content; old content must no longer match.
    lexical.upsert(fts_session, "d1", "golang concurrency", "acos_experiences")
    fts_session.commit()
    assert lexical.search(fts_session, "kubernetes", ["acos_experiences"], k=5) == []
    assert [r["id"] for r in lexical.search(fts_session, "golang", ["acos_experiences"], k=5)] == ["d1"]


def test_delete_removes_from_index(fts_session):
    _seed(fts_session)
    lexical.delete(fts_session, "d1")
    fts_session.commit()
    assert lexical.search(fts_session, "python performance tuning", ["acos_experiences"], k=5) == [
        r for r in lexical.search(fts_session, "python performance tuning", ["acos_experiences"], k=5)
        if r["id"] != "d1"
    ]
    assert all(r["id"] != "d1" for r in lexical.search(fts_session, "python", ["acos_experiences"], k=5))


def test_search_sanitizes_fts5_special_chars(fts_session):
    """Raw user text with FTS5 operators must not raise a syntax error."""
    _seed(fts_session)
    # Quotes, NEAR, column-filter colon, prefix star, parens — all special in FTS5.
    weird = 'python "perf* (tuning) NEAR/3 -event: ^loop'
    results = lexical.search(fts_session, weird, ["acos_experiences"], k=5)
    assert any(r["id"] == "d1" for r in results)
