"""Phase 12.6 AC4 — background ingestion.

POST /ingest returns 202 + job id immediately; the pipeline runs in a
BackgroundTask on a FRESH session; final job state is queryable; failures land
in ingestion_failures; file-security validation runs BEFORE the 202.

FastAPI's TestClient runs background tasks synchronously after the response is
sent, so by the time `client.post(...)` returns the job has already reached a
terminal state — we assert on that.
"""
from __future__ import annotations

import io
from contextlib import contextmanager
from unittest.mock import patch

import pytest

import backend.ingestion.jobs as ing
from backend.models.ingestion_failure import IngestionFailure


@pytest.fixture
def _bg_session(test_session, monkeypatch):
    """Route the background task's fresh session onto the in-memory test DB."""

    @contextmanager
    def _factory():
        yield test_session  # fixture owns lifecycle; don't close here

    monkeypatch.setattr(ing, "BACKGROUND_SESSION_FACTORY", _factory)
    yield


@pytest.fixture(autouse=True)
def _clear_jobs():
    ing.JOBS.clear()
    yield
    ing.JOBS.clear()


def _ok_patches():
    # Keep the pipeline hermetic: no real Ollama generate (entity extraction) or
    # embed round trips. is_available=False so the extractor stays regex-only.
    return (
        patch("backend.services.ollama_client.OllamaClient.is_available", return_value=False),
        patch("backend.services.ollama_client.OllamaClient.embed", return_value=[0.1] * 768),
        patch("backend.services.ollama_client.OllamaClient.embed_batch", return_value=[[0.1] * 768]),
        patch("backend.ingestion.entity_extractor.EntityExtractor.extract",
              return_value={"skills": []}),
    )


def test_ingest_returns_202_with_job_id_and_reaches_done(client, _bg_session):
    p1, p2, p3, p4 = _ok_patches()
    with p1, p2, p3, p4, patch("chromadb.PersistentClient"):
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("resume.txt", io.BytesIO(b"Senior engineer. Led Python work."), "text/plain")},
        )
    assert resp.status_code == 202
    body = resp.json()
    job_id = body["job_id"]
    assert body["status"] in {"queued", "processing", "done"}

    # background task already ran under TestClient → terminal state queryable
    status = client.get(f"/api/v1/ingest/{job_id}")
    assert status.status_code == 200
    sbody = status.json()
    assert sbody["status"] == "done"
    assert sbody["document_id"]


def test_bad_extension_rejected_before_202_no_job_created(client, _bg_session):
    resp = client.post(
        "/api/v1/ingest",
        files={"file": ("malware.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert ing.JOBS == {}  # validation failed before any job was registered


def test_oversize_rejected_before_202(client, _bg_session):
    with patch("backend.api.v1.routes.ingestion.security.validate_size",
               side_effect=ValueError("too big")):
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("big.txt", io.BytesIO(b"x" * 10), "text/plain")},
        )
    assert resp.status_code == 422
    assert ing.JOBS == {}


def test_failure_marks_job_failed_and_records_ingestion_failure(client, _bg_session, test_session):
    p1, p2, p3, p4 = _ok_patches()
    # Chroma indexing blows up → pipeline marks the doc failed and raises; ingest_safe
    # dead-letters it to ingestion_failures and the job ends 'failed'.
    with p1, p2, p3, p4, patch("chromadb.PersistentClient"), patch(
        "backend.rag.indexer.RAGIndexer.index_document",
        side_effect=RuntimeError("chroma down"),
    ):
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("notes.txt", io.BytesIO(b"some content here"), "text/plain")},
        )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    assert ing.JOBS[job_id].status == "failed"
    failures = test_session.query(IngestionFailure).all()
    assert len(failures) == 1


def test_unknown_job_returns_404(client, _bg_session):
    assert client.get("/api/v1/ingest/nonexistent").status_code == 404


def test_progress_stream_emits_terminal_event(client, _bg_session):
    p1, p2, p3, p4 = _ok_patches()
    with p1, p2, p3, p4, patch("chromadb.PersistentClient"):
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("r.txt", io.BytesIO(b"engineer content"), "text/plain")},
        )
    job_id = resp.json()["job_id"]
    stream = client.get(f"/api/v1/ingest/{job_id}/stream")
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers["content-type"]
    assert '"status": "done"' in stream.text or '"status":"done"' in stream.text
