from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_copilot_chat_with_ollama_unavailable_returns_context(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama

        mock_ret = MagicMock()
        mock_ret.retrieve.return_value = [
            {"id": "d1", "text": "Led Python work at Acme", "collection": "acos_experiences",
             "semantic_score": 0.9, "metadata": {"confidence_level": "verified", "entity_id": "e1"}}
        ]
        mock_ret_cls.return_value = mock_ret

        mock_rnk = MagicMock()
        mock_rnk.rerank.side_effect = lambda q, r, **kw: r
        mock_rnk_cls.return_value = mock_rnk

        resp = client.post("/api/v1/copilot/chat", json={"message": "What Python work have I done?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "intent" in data
    assert "citations" in data
    assert "evidence_count" in data


def test_copilot_chat_empty_message(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={"message": ""})
    assert resp.status_code == 200


def test_copilot_chat_with_history(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={
            "message": "Tell me more",
            "conversation_history": [
                {"role": "user", "content": "What Python work have I done?"},
                {"role": "assistant", "content": "You worked on ETL pipelines."},
            ],
        })
    assert resp.status_code == 200


def test_copilot_chat_missing_message_returns_422(client):
    resp = client.post("/api/v1/copilot/chat", json={})
    assert resp.status_code == 422


def test_copilot_chat_detects_resume_intent(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={"message": "Help me tailor my resume"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "resume_help"
