from unittest.mock import MagicMock

import pytest


def test_rag_service_returns_evidence_structure():
    from backend.services.rag.service import RAGService

    retriever = MagicMock()
    retriever.retrieve.return_value = [
        {
            "id": "exp1",
            "text": "Built Python library for litigation analytics.",
            "metadata": {"confidence_level": "verified", "entity_id": "exp1"},
            "semantic_score": 0.91,
            "collection": "acos_experiences",
        }
    ]
    reranker = MagicMock()
    reranker.rerank.return_value = [
        {
            "id": "exp1",
            "text": "Built Python library for litigation analytics.",
            "metadata": {"confidence_level": "verified", "entity_id": "exp1"},
            "semantic_score": 0.91,
            "combined_score": 1.09,
            "collection": "acos_experiences",
        }
    ]
    ollama = None

    svc = RAGService(retriever, reranker, ollama)
    result = svc.query("Python experience", intent="knowledge_lookup")

    assert "response" in result
    assert "evidence" in result
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["confidence"] == "verified"
    assert result["confidence_summary"] == "verified"


def test_rag_service_no_results():
    from backend.services.rag.service import RAGService

    retriever = MagicMock()
    retriever.retrieve.return_value = []
    reranker = MagicMock()
    reranker.rerank.return_value = []

    svc = RAGService(retriever, reranker, None)
    result = svc.query("unknown topic")
    assert result["evidence"] == []
    assert result["confidence_summary"] == "no_evidence"
