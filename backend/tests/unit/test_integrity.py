"""TDD for SQLite + Chroma + embedding integrity checks (Phase 11.1)."""
from unittest.mock import MagicMock

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401 — register models
from backend.models.base import Base
from backend.models.experience import Experience, ExperienceBullet
from backend.models.system_config import SystemConfig
from backend.services import integrity


def test_sqlite_integrity_clean_db(test_session):
    assert integrity.sqlite_integrity(test_session) == "ok"


def test_foreign_key_check_clean_db(test_session):
    assert integrity.foreign_key_check(test_session) == 0


def test_foreign_key_check_detects_orphan():
    # Build an engine WITHOUT FK enforcement so we can plant an orphan row.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    exp = Experience(
        title="X", company="Y", employment_type="full_time",
        start_date="2020-01", source="manual", tenant_id="default",
    )
    session.add(exp)
    session.flush()
    session.add(
        ExperienceBullet(
            experience_id="does-not-exist",
            bullet_text="orphan bullet",
            confidence_level="verified",
            order_index=0,
        )
    )
    session.flush()
    assert integrity.foreign_key_check(session) >= 1
    session.close()


def test_chroma_reconcile_consistent(test_session):
    test_session.add(
        Experience(title="X", company="Y", employment_type="full_time",
                   start_date="2020-01", source="manual")
    )
    test_session.flush()
    chroma = MagicMock()
    chroma.count.return_value = 10  # plenty of vectors
    result = integrity.chroma_reconcile(test_session, chroma)
    assert result["reconciled"] is True
    assert result["sqlite_documents"] >= 0
    assert result["chroma_vectors"] >= 0


def test_chroma_reconcile_flags_missing_vectors(test_session):
    from backend.repositories.document import DocumentRepository

    repo = DocumentRepository(test_session)
    repo.create(
        filename="r.txt", original_path="/r.txt", file_type="txt",
        file_size_bytes=1, checksum_sha256="abc", source_type="other",
        ingestion_status="complete", metadata_json={},
    )
    test_session.flush()
    chroma = MagicMock()
    chroma.count.return_value = 0  # no vectors at all → missing
    result = integrity.chroma_reconcile(test_session, chroma)
    assert result["reconciled"] is False


def test_chroma_reconcile_handles_unavailable(test_session):
    chroma = MagicMock()
    chroma.count.side_effect = RuntimeError("chroma down")
    result = integrity.chroma_reconcile(test_session, chroma)
    assert result["reconciled"] is False
    assert result["chroma_vectors"] is None
    assert "reason" in result


def test_embedding_status_current(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="nomic-embed-text"))
    test_session.flush()
    assert integrity.embedding_status(test_session, "nomic-embed-text") == "current"


def test_embedding_status_stale(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="old-model"))
    test_session.flush()
    assert integrity.embedding_status(test_session, "nomic-embed-text") == "stale"


def test_embedding_status_unknown_when_unrecorded(test_session):
    assert integrity.embedding_status(test_session, "nomic-embed-text") == "unknown"
