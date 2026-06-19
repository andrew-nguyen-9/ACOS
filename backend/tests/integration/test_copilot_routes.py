from __future__ import annotations

from unittest.mock import patch, MagicMock


def _mock_rag_result(response="Test answer", confidence="strong_inference"):
    return {
        "response": response,
        "evidence": [
            {
                "source": "acos_experiences",
                "text": "Led a team of 5 engineers at Acme Corp",
                "confidence": "verified",
                "similarity_score": 0.9,
            }
        ],
        "confidence_summary": confidence,
    }


def test_copilot_chat_basic(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "Tell me about my background"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "intent" in data
    assert "confidence" in data
    assert "citations" in data
    assert "evidence_count" in data


def test_copilot_chat_with_history(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={
                "message": "What did I do at Acme?",
                "conversation_history": [
                    {"role": "user", "content": "Tell me about my experience"},
                    {"role": "assistant", "content": "You worked at multiple companies."},
                ],
            },
        )
    assert resp.status_code == 200
    assert "response" in resp.json()


def test_copilot_chat_intent_inferred(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "Help me fix my resume for this job"},
        )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "resume_help"


def test_copilot_chat_interview_intent(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "How should I prepare for my interview tomorrow?"},
        )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "interview_prep"


def test_copilot_list_intents(client):
    resp = client.get("/api/v1/copilot/intents")
    assert resp.status_code == 200
    data = resp.json()
    assert "intents" in data
    intents = data["intents"]
    assert "resume_help" in intents
    assert "cover_letter_help" in intents
    assert "interview_prep" in intents
    assert "job_fit_analysis" in intents
    assert "career_advice" in intents
    assert "knowledge_lookup" in intents


def test_copilot_chat_citations_present(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "What is my most recent job?"},
        )
    assert resp.status_code == 200
    citations = resp.json()["citations"]
    assert len(citations) == 1
    assert citations[0]["source"] == "acos_experiences"
    assert citations[0]["confidence"] == "verified"
