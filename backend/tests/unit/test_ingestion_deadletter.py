"""TDD for resilient ingestion wrapper: retry + dead-letter (Phase 11.1)."""
from unittest.mock import MagicMock

from backend.ingestion.errors import PermanentError, TransientError
from backend.ingestion.pipeline import IngestionPipeline
from backend.models.ingestion_failure import IngestionFailure


def _pipeline(session) -> IngestionPipeline:
    return IngestionPipeline(session, MagicMock(), MagicMock(), MagicMock())


def test_ingest_safe_success(test_session):
    p = _pipeline(test_session)
    p.ingest = MagicMock(return_value="doc123")  # type: ignore[method-assign]
    result = p.ingest_safe("x.txt", sleep=lambda _: None)
    assert result == {"status": "ok", "document_id": "doc123"}
    assert test_session.query(IngestionFailure).count() == 0


def test_ingest_safe_retries_transient_then_succeeds(test_session):
    p = _pipeline(test_session)
    calls = {"n": 0}

    def flaky(_path):
        calls["n"] += 1
        if calls["n"] < 2:
            raise TransientError("file locked")
        return "doc1"

    p.ingest = flaky  # type: ignore[method-assign]
    result = p.ingest_safe("x.txt", sleep=lambda _: None)
    assert result["status"] == "ok"
    assert calls["n"] == 2
    assert test_session.query(IngestionFailure).count() == 0


def test_ingest_safe_transient_exhausted_deadletters(test_session):
    p = _pipeline(test_session)
    p.ingest = MagicMock(side_effect=TransientError("file locked"))  # type: ignore[method-assign]
    result = p.ingest_safe("x.txt", attempts=3, sleep=lambda _: None)
    assert result["status"] == "failed"
    assert p.ingest.call_count == 3
    row = test_session.query(IngestionFailure).one()
    assert row.error_type == "transient"
    assert row.attempts == 3
    assert row.path == "x.txt"


def test_ingest_safe_permanent_deadletters_immediately(test_session):
    p = _pipeline(test_session)
    p.ingest = MagicMock(side_effect=PermanentError("unsupported type"))  # type: ignore[method-assign]
    result = p.ingest_safe("x.bin", attempts=3, sleep=lambda _: None)
    assert result["status"] == "failed"
    assert p.ingest.call_count == 1  # permanent errors are not retried
    row = test_session.query(IngestionFailure).one()
    assert row.error_type == "permanent"


def test_ingest_safe_unknown_error_treated_as_permanent(test_session):
    p = _pipeline(test_session)
    p.ingest = MagicMock(side_effect=ValueError("boom"))  # type: ignore[method-assign]
    result = p.ingest_safe("x.txt", attempts=3, sleep=lambda _: None)
    assert result["status"] == "failed"
    assert p.ingest.call_count == 1  # don't retry unknowns — could mask a real bug
    row = test_session.query(IngestionFailure).one()
    assert row.error_type == "permanent"
