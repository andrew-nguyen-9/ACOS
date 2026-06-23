from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_ollama_and_chroma():
    """Mock OllamaClient, RAGRetriever, Reranker, and ChromaManager to prevent hangs when Ollama is offline."""
    mock_ollama = MagicMock()
    mock_ollama.is_available.return_value = False
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = []
    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    with (
        patch("backend.api.v1.routes.questions.OllamaClient", return_value=mock_ollama),
        patch("backend.api.v1.routes.questions.RAGRetriever", return_value=mock_retriever),
        patch("backend.api.v1.routes.questions.Reranker", return_value=mock_reranker),
        patch("backend.api.v1.routes.questions.get_chroma_manager", return_value=MagicMock()),
    ):
        yield


def test_generate_questions(client):
    resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Python engineer needed", "company": "Acme", "position": "Engineer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) > 0
    q = data["questions"][0]
    assert "id" in q
    assert "question_template" in q
    assert "interpolated" in q
    assert "category" in q


def test_generate_answer(client):
    # First generate a question
    gen_resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Python engineer", "company": "Acme", "position": "Dev"},
    )
    q_id = gen_resp.json()["questions"][0]["id"]

    resp = client.post(
        f"/api/v1/questions/{q_id}/answer",
        json={"variables": {"company": "Acme", "position": "Dev"}, "length_target": "short"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer_id" in data
    assert "original_answer" in data
    assert "confidence_level" in data
    assert data["confidence_level"] in ("verified", "strong_inference", "weak_inference")
    assert "requires_approval" in data


def test_generate_answer_invalid_length(client):
    gen_resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Dev role"},
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    resp = client.post(f"/api/v1/questions/{q_id}/answer", json={"length_target": "huge"})
    assert resp.status_code == 422


def test_generate_answer_question_not_found(client):
    resp = client.post("/api/v1/questions/doesnotexist/answer", json={})
    assert resp.status_code == 404


def test_edit_answer(client):
    gen_resp = client.post(
        "/api/v1/questions/generate", json={"job_description": "Dev role"}
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    ans_resp = client.post(f"/api/v1/questions/{q_id}/answer", json={})
    answer_id = ans_resp.json()["answer_id"]

    edit_resp = client.patch(
        f"/api/v1/questions/{q_id}/answers/{answer_id}",
        json={"edited_text": "My refined answer", "diff_summary": "Improved tone"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["edited_answer"] == "My refined answer"


def test_edit_answer_not_found(client):
    resp = client.patch(
        "/api/v1/questions/q1/answers/doesnotexist",
        json={"edited_text": "text"},
    )
    assert resp.status_code == 404


def test_list_questions_empty(client):
    resp = client.get("/api/v1/questions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_questions_after_generation(client):
    client.post("/api/v1/questions/generate", json={"job_description": "Dev role"})
    resp = client.get("/api/v1/questions")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_questions_filter_by_category(client):
    client.post("/api/v1/questions/generate", json={"job_description": "Dev role"})
    resp = client.get("/api/v1/questions?category=behavioral")
    assert resp.status_code == 200
    for q in resp.json():
        assert q["category"] == "behavioral"


def test_list_answers_for_question(client):
    gen_resp = client.post(
        "/api/v1/questions/generate", json={"job_description": "Dev role"}
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    client.post(f"/api/v1/questions/{q_id}/answer", json={})
    resp = client.get(f"/api/v1/questions/{q_id}/answers")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_answers_question_not_found(client):
    resp = client.get("/api/v1/questions/doesnotexist/answers")
    assert resp.status_code == 404


# ── 15.3 — interview simulation deepening ─────────────────────────────────────

def test_generate_questions_accepts_persona(client):
    resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Python engineer needed", "persona": "skeptical"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) > 0


def test_followups_route_returns_list(client):
    # Ollama mocked unavailable (autouse) → deterministic fallback follow-ups.
    resp = client.post(
        "/api/v1/questions/followups",
        json={"question": "Tell me about a project.", "answer_text": "I led a migration.", "max_followups": 2},
    )
    assert resp.status_code == 200
    followups = resp.json()["followups"]
    assert isinstance(followups, list)
    assert len(followups) == 2


def test_evaluate_route_grounds_in_kg(client):
    # Empty graph → honest zero coverage + weak confidence, never a fabricated score.
    resp = client.post(
        "/api/v1/questions/evaluate",
        json={"answer_text": "I built ETL pipelines in Python."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["coverage"] == 0.0
    assert data["confidence"] == "weak_inference"
    assert "covered_node_ids" in data
