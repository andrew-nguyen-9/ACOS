"""
End-to-end pipeline integration test — single function, sequential, state-threaded.

Validates all 8 spec steps:
  1. Health check
  2. Document ingestion  → document_id
  3. Onboarding status   → completed: false
  4. Complete onboarding → completed: true
  5. RAG query           → response + evidence
  6. Resume generation   → 200 + content_json
  7. Applications CRM    → create + status transition
  8. Learning loop       → record outcome + report count >= 1

Mocks: Ollama (is_available=True, generate, embed, list_models) + ChromaDB PersistentClient.
No live services required.
"""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.database import seed_system_config


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_JD = """
We are seeking a Senior Data Engineer to join our team.
Requirements: Python, SQL, Apache Spark, data pipeline design, ETL,
AWS, Kafka, experience with large-scale distributed systems.
Minimum 5 years of experience in data engineering.
"""

SAMPLE_RESUME_TEXT = """
Andrew Nguyen - Data Engineer
Experience: 7 years of Python, SQL, Spark, Kafka, AWS.
Led migration of ETL pipeline processing 10M records/day.
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_config(test_session):
    """Seed system config rows so settings routes work."""
    seed_system_config(test_session)
    test_session.commit()
    yield


def _make_chroma_mock() -> MagicMock:
    """
    Return a mock that satisfies the chromadb.PersistentClient interface.

    ChromaManager calls:
      client.get_or_create_collection(name, metadata=...) → collection
      collection.upsert(...)
      collection.add(...)
      collection.query(query_embeddings=..., n_results=...) → dict
      collection.count() → int
      client.heartbeat()

    The query result uses distance=0.1 so semantic_score = 1.0 - 0.1 = 0.9,
    which passes RAGRetriever's MIN_SIMILARITY=0.35 filter and produces evidence.
    """
    fake_result = {
        "ids": [["doc-1"]],
        "documents": [["Sample text about Python SQL data engineering"]],
        "metadatas": [[{
            "source": "test",
            "confidence_level": "strong_inference",
            "experience_id": "exp-1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "start_date": "2020-01",
            "end_date": "Present",
        }]],
        "distances": [[0.1]],
    }

    mock_collection = MagicMock()
    mock_collection.upsert.return_value = None
    mock_collection.add.return_value = None
    mock_collection.query.return_value = fake_result
    mock_collection.count.return_value = 1

    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_client.heartbeat.return_value = True

    return mock_client


# ---------------------------------------------------------------------------
# The single E2E test function
# ---------------------------------------------------------------------------

def test_full_pipeline(client, seed_config, test_session):
    """
    Full 8-step pipeline test.  Each step's output feeds the next.
    is_available=True so resume/RAG code paths fully execute (LLM JSON
    parse failure triggers rule-based fallback, which still returns content_json).
    """
    chroma_mock = _make_chroma_mock()

    from contextlib import contextmanager

    @contextmanager
    def _bg_session():
        # 12.6 background ingest opens a FRESH session; route it onto the test DB.
        yield test_session

    with (
        patch("backend.ingestion.jobs.BACKGROUND_SESSION_FACTORY", _bg_session),
        patch(
            "backend.services.ollama_client.OllamaClient.is_available",
            return_value=True,
        ),
        patch(
            "backend.services.ollama_client.OllamaClient.generate",
            return_value="Mocked LLM output",
        ),
        patch(
            "backend.services.ollama_client.OllamaClient.embed",
            return_value=[0.1] * 768,
        ),
        patch(
            "backend.services.ollama_client.OllamaClient.list_models",
            return_value=["qwen3:8b", "nomic-embed-text"],
        ),
        patch(
            "chromadb.PersistentClient",
            return_value=chroma_mock,
        ),
    ):
        # ------------------------------------------------------------------
        # Step 1: Health check
        # ------------------------------------------------------------------
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200, f"Step 1 health: {resp.text}"
        assert resp.json()["status"] == "ok", f"Step 1 body: {resp.json()}"

        # ------------------------------------------------------------------
        # Step 2: Ingest a text file → extract document_id
        # ------------------------------------------------------------------
        file_bytes = SAMPLE_RESUME_TEXT.encode()
        resp = client.post(
            "/api/v1/ingest",
            files={"file": ("resume.txt", io.BytesIO(file_bytes), "text/plain")},
        )
        # 12.6: ingestion is now async — 202 + job id; the background task already
        # ran (TestClient runs it before returning), so the job is terminal.
        assert resp.status_code == 202, f"Step 2 ingest: {resp.text}"
        job_id = resp.json()["job_id"]
        status = client.get(f"/api/v1/ingest/{job_id}")
        assert status.status_code == 200, f"Step 2 status: {status.text}"
        assert status.json()["status"] == "done", f"Step 2 job not done: {status.json()}"
        document_id = status.json()["document_id"]
        assert document_id, "Step 2: document_id must be non-empty"

        # ------------------------------------------------------------------
        # Step 3: Onboarding status → completed: false
        # ------------------------------------------------------------------
        resp = client.get("/api/v1/settings/onboarding")
        assert resp.status_code == 200, f"Step 3 onboarding GET: {resp.text}"
        assert resp.json() == {"completed": False}, f"Step 3 body: {resp.json()}"

        # ------------------------------------------------------------------
        # Step 4: Complete onboarding → completed: true
        # ------------------------------------------------------------------
        resp = client.post("/api/v1/settings/onboarding/complete")
        assert resp.status_code == 200, f"Step 4 onboarding POST: {resp.text}"
        assert resp.json().get("completed") is True, f"Step 4 body: {resp.json()}"

        # ------------------------------------------------------------------
        # Step 5: RAG query — pass document_id context; assert 200 + response field
        # ------------------------------------------------------------------
        resp = client.post(
            "/api/v1/rag/query",
            json={
                "query": f"data engineering Python SQL (doc_id={document_id})",
                "intent": "knowledge_lookup",
            },
        )
        assert resp.status_code == 200, f"Step 5 rag/query: {resp.text}"
        rag_data = resp.json()
        assert "response" in rag_data, f"Step 5 missing 'response': {rag_data}"
        assert "evidence" in rag_data, f"Step 5 missing 'evidence': {rag_data}"

        # ------------------------------------------------------------------
        # Step 6: Resume generation → 200 + content_json key
        # Note: generate() returns "Mocked LLM output" which fails json.loads(),
        # so ResumeGenerator falls back to rule-based build; content_json is still
        # populated from the ChromaDB evidence returned above.
        # ------------------------------------------------------------------
        resp = client.post(
            "/api/v1/resume/generate",
            json={"job_description": SAMPLE_JD, "template_name": "software"},
        )
        assert resp.status_code == 200, f"Step 6 resume/generate: {resp.text}"
        resume_data = resp.json()
        assert "content_json" in resume_data, f"Step 6 missing 'content_json': {resume_data}"

        # ------------------------------------------------------------------
        # Step 7: Applications CRM — create + status transition
        # ------------------------------------------------------------------
        resp = client.post(
            "/api/v1/applications",
            json={
                "company": "Acme Data Co",
                "position": "Senior Data Engineer",
                "industry": "Technology",
                "status": "draft",
            },
        )
        assert resp.status_code == 201, f"Step 7a create application: {resp.text}"
        app_data = resp.json()
        assert "id" in app_data, f"Step 7a missing 'id': {app_data}"
        app_id = app_data["id"]

        resp = client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "applied"},
        )
        assert resp.status_code == 200, f"Step 7b status transition: {resp.text}"
        assert resp.json()["status"] == "applied", f"Step 7b wrong status: {resp.json()}"

        # ------------------------------------------------------------------
        # Step 8: Learning loop — record outcome signal; report count >= 1
        # ------------------------------------------------------------------
        resp = client.post(
            "/api/v1/learning/outcome",
            json={
                "application_id": app_id,
                "signal_type": "phone_screen",
                "template_used": "software",
                "ats_score": 78.5,
            },
        )
        assert resp.status_code == 200, f"Step 8a learning/outcome: {resp.text}"
        outcome_data = resp.json()
        assert outcome_data.get("signal_type") == "phone_screen", (
            f"Step 8a unexpected signal_type: {outcome_data}"
        )

        resp = client.get("/api/v1/learning/report")
        assert resp.status_code == 200, f"Step 8b learning/report: {resp.text}"
        report_data = resp.json()
        assert "template_rankings" in report_data, (
            f"Step 8b missing 'template_rankings': {report_data}"
        )
        rankings = report_data["template_rankings"]
        assert len(rankings) >= 1, f"Step 8b expected >= 1 ranking, got: {rankings}"
