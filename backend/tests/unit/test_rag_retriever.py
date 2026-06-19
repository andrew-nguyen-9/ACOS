from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.rag.retriever import RAGRetriever


def _make_chroma_response(ids, docs, metas, distances):
    return {
        "ids": [ids],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
    }


@pytest.fixture
def retriever():
    chroma = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [0.1, 0.2, 0.3]
    return RAGRetriever(chroma, embedder), chroma, embedder


def test_retrieve_returns_results_above_threshold(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Python engineer experience"],
        metas=[{"confidence_level": "verified"}],
        distances=[0.2],  # semantic_score = 1 - 0.2 = 0.8
    )
    results = rag.retrieve("Python engineer", ["acos_skills"])
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["semantic_score"] == pytest.approx(0.8)


def test_retrieve_filters_below_min_similarity(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Unrelated text"],
        metas=[{}],
        distances=[0.9],  # semantic_score = 0.1, below MIN_SIMILARITY=0.35
    )
    results = rag.retrieve("Python", ["acos_skills"])
    assert results == []


def test_retrieve_handles_chroma_exception_gracefully(retriever):
    rag, chroma, embedder = retriever
    chroma.query.side_effect = RuntimeError("chroma unavailable")
    results = rag.retrieve("Python", ["acos_skills"])
    assert results == []


def test_retrieve_multiple_collections(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Text"],
        metas=[{}],
        distances=[0.3],  # semantic_score = 0.7
    )
    results = rag.retrieve("Python", ["acos_skills", "acos_projects"])
    assert len(results) == 2
    assert chroma.query.call_count == 2


def test_retrieve_includes_collection_name(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Text"],
        metas=[{}],
        distances=[0.2],
    )
    results = rag.retrieve("query", ["acos_bullets"])
    assert results[0]["collection"] == "acos_bullets"
