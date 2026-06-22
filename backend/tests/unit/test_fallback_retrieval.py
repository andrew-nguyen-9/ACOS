"""TDD for RAG fallback mode when the vector store is unavailable (Phase 11.1)."""
from unittest.mock import MagicMock

from backend.models.experience import Experience, ExperienceBullet
from backend.rag.fallback import KeywordFallback
from backend.services.rag.service import RAGService


def _seed(session):
    exp = Experience(
        title="Data Engineer",
        company="Acme",
        employment_type="full_time",
        start_date="2022-01",
        source="manual",
    )
    session.add(exp)
    session.flush()
    session.add_all(
        [
            ExperienceBullet(
                experience_id=exp.id,
                bullet_text="Built Python ETL pipeline reducing processing time",
                confidence_level="verified",
                order_index=0,
            ),
            ExperienceBullet(
                experience_id=exp.id,
                bullet_text="Led stakeholder workshops for roadmap planning",
                confidence_level="strong_inference",
                order_index=1,
            ),
        ]
    )
    session.flush()


# ── KeywordFallback ──────────────────────────────────────────────────────────

def test_search_ranks_by_term_overlap(test_session):
    _seed(test_session)
    results = KeywordFallback(test_session).search("python pipeline", top_k=5)
    assert results
    assert "python" in results[0]["text"].lower()
    assert results[0]["confidence"] == "verified"
    assert 0 < results[0]["similarity_score"] <= 1


def test_search_no_match_returns_empty(test_session):
    _seed(test_session)
    assert KeywordFallback(test_session).search("quantum astrobiology") == []


def test_search_empty_query_returns_empty(test_session):
    _seed(test_session)
    assert KeywordFallback(test_session).search("   ") == []


# ── RAGService degradation ───────────────────────────────────────────────────

def _fallback_stub():
    fb = MagicMock()
    fb.search.return_value = [
        {
            "text": "Built Python ETL pipeline",
            "source": "acos_experiences",
            "entity_id": "b1",
            "confidence": "verified",
            "similarity_score": 0.5,
        }
    ]
    return fb


def test_query_falls_back_when_retriever_empty():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    ollama = MagicMock()
    ollama.is_available.return_value = False
    svc = RAGService(retriever, MagicMock(), ollama, fallback=_fallback_stub())

    result = svc.query("python", intent="resume_help")

    assert result["degraded"] is True
    assert "degraded_reason" in result
    assert result["evidence"]


def test_query_degrades_on_retriever_exception():
    retriever = MagicMock()
    retriever.retrieve.side_effect = RuntimeError("chroma down")
    ollama = MagicMock()
    ollama.is_available.return_value = False
    svc = RAGService(retriever, MagicMock(), ollama, fallback=_fallback_stub())

    result = svc.query("python")

    assert result["degraded"] is True
    assert "chroma down" in result["degraded_reason"]


def test_query_happy_path_not_degraded():
    retriever = MagicMock()
    retriever.retrieve.return_value = [
        {"id": "a", "text": "x", "collection": "acos_experiences",
         "semantic_score": 0.9, "metadata": {"confidence_level": "verified"}},
    ]
    reranker = MagicMock()
    reranker.rerank.side_effect = lambda q, results, **kw: results
    ollama = MagicMock()
    ollama.is_available.return_value = False
    svc = RAGService(retriever, reranker, ollama, fallback=_fallback_stub())

    result = svc.query("python")

    assert result["degraded"] is False
    assert "degraded_reason" not in result
