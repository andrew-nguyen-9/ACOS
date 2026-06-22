from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.rag import lexical
from backend.services.rag.service import RAGService
from backend.services.resume.evidence_selector import EvidenceSelector


# ---------- fixtures ----------

@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {
            "id": "doc1",
            "text": "Led Python migration at Acme saving $200K.",
            "collection": "acos_experiences",
            "semantic_score": 0.92,
            "metadata": {
                "confidence_level": "verified",
                "entity_id": "exp1",
                "experience_id": "exp1",
                "company": "Acme",
                "title": "SWE",
                "start_date": "2022-01",
                "end_date": "Present",
            },
        }
    ]
    return r


@pytest.fixture
def mock_reranker():
    rr = MagicMock()
    rr.rerank.side_effect = lambda query, results, **kwargs: results
    return rr


@pytest.fixture
def mock_ollama_unavailable():
    o = MagicMock()
    o.is_available.return_value = False
    return o


@pytest.fixture
def mock_ollama_available():
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = "Here is a summary of your experience."
    return o


# ---------- RAGService tests ----------

def test_query_no_ollama_returns_context_text(mock_retriever, mock_reranker, mock_ollama_unavailable):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_unavailable)
    result = svc.query("Tell me about Python work", intent="resume_help")
    assert "response" in result
    assert "evidence" in result
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["confidence"] == "verified"


def test_query_with_ollama_calls_generate(mock_retriever, mock_reranker, mock_ollama_available):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_available)
    result = svc.query("Tell me about Python work", intent="resume_help")
    mock_ollama_available.generate.assert_called_once()
    assert result["response"] == "Here is a summary of your experience."


def test_query_empty_evidence_returns_no_evidence_response(mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything", intent="knowledge_lookup")
    assert result["response"] == "No relevant context found."
    assert result["confidence_summary"] == "no_evidence"


def test_query_unknown_intent_defaults_to_knowledge_lookup(mock_retriever, mock_reranker, mock_ollama_unavailable):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything", intent="totally_unknown_intent")
    assert "evidence" in result


def test_summarize_confidence_verified_beats_weak(mock_retriever, mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = [
        {"id": "a", "text": "x", "collection": "acos_experiences", "semantic_score": 0.9,
         "metadata": {"confidence_level": "weak_inference"}},
        {"id": "b", "text": "y", "collection": "acos_experiences", "semantic_score": 0.8,
         "metadata": {"confidence_level": "verified"}},
    ]
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything")
    assert result["confidence_summary"] == "verified"


def test_query_career_advice_intent_uses_all_collections(mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    svc.query("help me grow my career", intent="career_advice")
    call_args = r.retrieve.call_args
    collections = call_args[0][1] if call_args[0] else call_args[1]["collections"]
    assert "acos_github" in collections
    assert "acos_claude_exports" in collections


def test_query_fuses_fts5_lexical_leg(mock_retriever, mock_reranker, mock_ollama_unavailable):
    """With a session, the FTS5 lexical leg unions keyword-only recall into the
    candidates the reranker sees (dense leg is mocked to return only doc1)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    lexical.ensure_fts5(session)
    lexical.upsert(session, "lexdoc", "python kubernetes deployment orchestration", "acos_experiences")
    session.commit()
    try:
        svc = RAGService(
            mock_retriever, mock_reranker, mock_ollama_unavailable, session=session
        )
        result = svc.query("python kubernetes", intent="resume_help")
        ids = {e["entity_id"] for e in result["evidence"]}
        assert "lexdoc" in ids  # lexical-only hit reached the reranker
    finally:
        session.close()
        engine.dispose()


def test_query_without_session_skips_lexical_leg(mock_retriever, mock_reranker, mock_ollama_unavailable):
    """No session → dense-only, no FTS5 call, no crash (backward compat)."""
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything", intent="resume_help")
    assert len(result["evidence"]) == 1


# ---------- EvidenceSelector tests ----------

def test_evidence_selector_returns_bullets(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    bullets = selector.select("Python engineering role", {})
    assert len(bullets) == 1
    assert bullets[0]["bullet_text"] == "Led Python migration at Acme saving $200K."
    assert bullets[0]["confidence"] == "verified"
    assert bullets[0]["company"] == "Acme"


def test_evidence_selector_fuses_fts5_lexical_leg(mock_retriever, mock_reranker):
    """The resume evidence path also unions the FTS5 lexical leg (equal-or-better
    than the old in-set BM25), so keyword-only experience hits reach selection."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session = sessionmaker(bind=engine)()
    lexical.ensure_fts5(session)
    lexical.upsert(session, "lexbullet", "led terraform infrastructure automation rollout", "acos_experiences")
    session.commit()
    try:
        selector = EvidenceSelector(mock_retriever, mock_reranker, session=session)
        bullets = selector.select("terraform infrastructure automation", {}, max_bullets=8)
        assert any(b["evidence_id"] == "lexbullet" for b in bullets)
    finally:
        session.close()
        engine.dispose()


def test_evidence_selector_empty_returns_empty(mock_reranker):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("anything", {})
    assert bullets == []


def test_evidence_selector_respects_max_bullets(mock_reranker):
    raw = [
        {"id": f"d{i}", "text": f"bullet {i}", "collection": "acos_experiences",
         "semantic_score": 0.9,
         "metadata": {"confidence_level": "strong_inference", "experience_id": f"e{i}",
                      "company": "Co", "title": "Eng", "start_date": "2020-01", "end_date": "2022-01"}}
        for i in range(20)
    ]
    r = MagicMock()
    r.retrieve.return_value = raw
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("Python role", {}, max_bullets=3)
    assert len(bullets) <= 3


def test_evidence_selector_dates_formatted(mock_reranker):
    r = MagicMock()
    r.retrieve.return_value = [
        {"id": "x", "text": "did stuff", "collection": "acos_experiences", "semantic_score": 0.5,
         "metadata": {"confidence_level": "verified", "start_date": "2021-03", "end_date": "2023-09",
                      "company": "Biz", "title": "Lead"}}
    ]
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("anything", {})
    assert "2021-03" in bullets[0]["dates"]
    assert "2023-09" in bullets[0]["dates"]
