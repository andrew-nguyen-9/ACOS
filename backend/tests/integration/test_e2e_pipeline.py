"""
End-to-end pipeline integration test.
Validates: ingestion → RAG → resume generation → ATS → CRM → copilot → learning loop
Uses mocked Ollama and ChromaDB so no live services are required.
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from backend.database import seed_system_config


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


@pytest.fixture(autouse=True)
def seed_config(test_session):
    """Seed system config rows so settings routes work."""
    seed_system_config(test_session)
    test_session.commit()


def _make_chroma_mock() -> MagicMock:
    """Return a ChromaManager-like mock that satisfies upsert/query/count calls."""
    mock = MagicMock()
    collection = MagicMock()
    collection.upsert.return_value = None
    collection.add.return_value = None
    collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    collection.count.return_value = 0
    mock.get_or_create_collection.return_value = collection
    mock.upsert.return_value = None
    mock.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    mock.count.return_value = 0
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def mock_external_services():
    """Stub all network-bound services: Ollama + ChromaDB PersistentClient."""
    chroma_instance = _make_chroma_mock()

    with (
        patch(
            "backend.services.ollama_client.OllamaClient.is_available",
            return_value=False,  # drives RAGService to skip LLM generation
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
            return_value=chroma_instance,
        ),
    ):
        yield


# ---------------------------------------------------------------------------
# Helper: ingest a document and return its document_id
# ---------------------------------------------------------------------------

def _ingest_txt(client, text: str, filename: str = "resume.txt") -> str:
    file_content = text.encode()
    resp = client.post(
        "/api/v1/ingest",
        files={"file": (filename, io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "document_id" in data, f"Expected 'document_id' in {data}"
    return data["document_id"]


# ---------------------------------------------------------------------------
# Step 1: Ingest a text document
# ---------------------------------------------------------------------------

def test_ingest_txt_document(client, mock_external_services):
    """Ingest a plain-text resume; expect a document_id back."""
    doc_id = _ingest_txt(client, SAMPLE_RESUME_TEXT, "my_resume.txt")
    assert doc_id, "Expected a non-empty document_id"


# ---------------------------------------------------------------------------
# Step 2: RAG query returns a response structure
# ---------------------------------------------------------------------------

def test_rag_query_returns_evidence(client, mock_external_services):
    """RAG query endpoint returns response + evidence list."""
    resp = client.post(
        "/api/v1/rag/query",
        json={"query": "data engineering Python SQL", "intent": "knowledge_lookup"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "evidence" in data, f"Expected 'evidence' key in {data}"
    assert "response" in data, f"Expected 'response' key in {data}"


# ---------------------------------------------------------------------------
# Step 3: Resume generation endpoint accepts a valid template
# ---------------------------------------------------------------------------

def test_resume_generate_endpoint_reachable(client, mock_external_services):
    """Resume generation returns 200/422 (not 404/500); endpoint is wired up."""
    resp = client.post(
        "/api/v1/resume/generate",
        json={"job_description": SAMPLE_JD, "template_name": "software"},
    )
    # 200 = success; 422 = validation error from generator (no evidence), both are acceptable
    assert resp.status_code in (200, 422), resp.text


# ---------------------------------------------------------------------------
# Step 4: ATS analysis returns ats_score
# ---------------------------------------------------------------------------

def test_ats_analysis_returns_score(client, mock_external_services):
    """ATS analysis endpoint returns ats_score."""
    resp = client.post(
        "/api/v1/resume/analyze-ats",
        json={
            "resume_text": SAMPLE_RESUME_TEXT,
            "job_description": SAMPLE_JD,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "ats_score" in data, f"Expected 'ats_score' in {data}"


# ---------------------------------------------------------------------------
# Step 5: Create application, transition status, check timeline
# ---------------------------------------------------------------------------

def test_application_create_and_status_transition(client, mock_external_services):
    """Create an application, transition status to applied, verify timeline."""
    create_resp = client.post(
        "/api/v1/applications",
        json={
            "company": "Acme Data Co",
            "position": "Senior Data Engineer",
            "industry": "Technology",
            "status": "draft",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    app_id = create_resp.json()["id"]

    status_resp = client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "applied"},
    )
    assert status_resp.status_code == 200, status_resp.text
    assert status_resp.json()["status"] == "applied"

    timeline_resp = client.get(f"/api/v1/applications/{app_id}/timeline")
    assert timeline_resp.status_code == 200, timeline_resp.text
    events = timeline_resp.json()
    assert any(e["to_status"] == "applied" for e in events), (
        f"Expected a timeline event with to_status='applied'. Got: {events}"
    )


# ---------------------------------------------------------------------------
# Step 6: Outcome signal is recorded via learning/outcome
# ---------------------------------------------------------------------------

def test_outcome_signal_recorded(client, mock_external_services):
    """Outcome signal feeds the learning loop and returns signal metadata."""
    create_resp = client.post(
        "/api/v1/applications",
        json={"company": "Beta Corp", "position": "PM", "status": "draft"},
    )
    assert create_resp.status_code == 201, create_resp.text
    app_id = create_resp.json()["id"]

    outcome_resp = client.post(
        "/api/v1/learning/outcome",
        json={
            "application_id": app_id,
            "signal_type": "phone_screen",
            "template_used": "standard_v1",
            "ats_score": 78.5,
        },
    )
    assert outcome_resp.status_code == 200, outcome_resp.text
    data = outcome_resp.json()
    assert data["signal_type"] == "phone_screen", f"Unexpected response: {data}"


# ---------------------------------------------------------------------------
# Step 7: Copilot chat responds with response + intent
# ---------------------------------------------------------------------------

def test_copilot_chat_responds(client, mock_external_services):
    """Copilot /chat returns response and intent classification."""
    resp = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What are my strongest data engineering skills?"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "response" in data, f"Expected 'response' in {data}"
    assert "intent" in data, f"Expected 'intent' in {data}"


# ---------------------------------------------------------------------------
# Step 8: Learning report reflects recorded signals
# ---------------------------------------------------------------------------

def test_learning_report_after_signal(client, mock_external_services):
    """Learning report lists template rankings after an outcome signal."""
    create_resp = client.post(
        "/api/v1/applications",
        json={"company": "Gamma Inc", "position": "Analyst", "status": "draft"},
    )
    assert create_resp.status_code == 201, create_resp.text
    app_id = create_resp.json()["id"]

    outcome_resp = client.post(
        "/api/v1/learning/outcome",
        json={
            "application_id": app_id,
            "signal_type": "interview",
            "template_used": "executive_v2",
            "ats_score": 85.0,
        },
    )
    assert outcome_resp.status_code == 200, outcome_resp.text

    report_resp = client.get("/api/v1/learning/report")
    assert report_resp.status_code == 200, report_resp.text
    data = report_resp.json()
    assert "template_rankings" in data, f"Expected 'template_rankings' in {data}"
    rankings = data["template_rankings"]
    assert any(r["template_name"] == "executive_v2" for r in rankings), (
        f"Expected 'executive_v2' in rankings. Got: {rankings}"
    )
