from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.rag.collections import DOCUMENTS
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


def test_retrieve_issues_single_query_against_documents_with_doctype_filter(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Python engineer experience"],
        metas=[{"confidence_level": "verified", "doc_type": "acos_skills"}],
        distances=[0.2],
    )
    results = rag.retrieve("Python engineer", ["acos_skills", "acos_experiences"])

    # consolidation: one physical query, not one per partition
    assert chroma.query.call_count == 1
    kwargs = chroma.query.call_args.kwargs
    assert kwargs["collection"] == DOCUMENTS
    assert kwargs["where"] == {"doc_type": {"$in": ["acos_skills", "acos_experiences"]}}
    assert results[0]["id"] == "doc1"
    assert results[0]["semantic_score"] == pytest.approx(0.8)


def test_retrieve_collection_field_comes_from_doctype_metadata(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Text"],
        metas=[{"doc_type": "acos_projects"}],
        distances=[0.2],
    )
    results = rag.retrieve("query", ["acos_projects"])
    assert results[0]["collection"] == "acos_projects"


def test_retrieve_filters_below_min_similarity(retriever):
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response(
        ids=["doc1"],
        docs=["Unrelated text"],
        metas=[{}],
        distances=[0.9],  # semantic_score = 0.1, below MIN_SIMILARITY=0.35
    )
    assert rag.retrieve("Python", ["acos_skills"]) == []


def test_retrieve_handles_chroma_exception_gracefully(retriever):
    rag, chroma, embedder = retriever
    chroma.query.side_effect = RuntimeError("chroma unavailable")
    assert rag.retrieve("Python", ["acos_skills"]) == []


def test_retrieve_empty_doc_types_returns_empty_without_querying(retriever):
    rag, chroma, embedder = retriever
    assert rag.retrieve("anything", []) == []
    chroma.query.assert_not_called()


def test_retrieve_scales_n_results_by_doctype_count(retriever):
    """n_results scales with partition count so multi-type intents keep recall."""
    rag, chroma, embedder = retriever
    chroma.query.return_value = _make_chroma_response([], [], [], [])
    rag.retrieve("q", ["acos_experiences", "acos_projects", "acos_skills"], top_k=10)
    assert chroma.query.call_args.kwargs["n_results"] == 30
