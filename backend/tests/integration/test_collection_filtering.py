"""Phase 12.6 AC1 — retrieval over the consolidated collection filters by doc_type.

Real ChromaDB (tmp dir), fake embedder — no Ollama. Proves the where-$in filter
returns only the requested partition from the single physical collection.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.rag.chroma_client import ChromaManager
from backend.rag.collections import DOCUMENTS
from backend.rag.retriever import RAGRetriever


def _seed(mgr: ChromaManager) -> None:
    mgr.add(
        DOCUMENTS,
        ids=["e1"],
        documents=["led python migration"],
        embeddings=[[1.0, 0.0, 0.0]],
        metadatas=[{"doc_type": "acos_experiences", "confidence_level": "verified"}],
    )
    mgr.add(
        DOCUMENTS,
        ids=["s1"],
        documents=["python skill"],
        embeddings=[[1.0, 0.05, 0.0]],
        metadatas=[{"doc_type": "acos_skills", "confidence_level": "verified"}],
    )
    mgr.add(
        DOCUMENTS,
        ids=["j1"],
        documents=["job description"],
        embeddings=[[1.0, 0.0, 0.02]],
        metadatas=[{"doc_type": "acos_job_descriptions", "confidence_level": "verified"}],
    )


def test_where_filter_returns_only_requested_doc_type(tmp_path):
    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    _seed(mgr)
    embedder = MagicMock()
    embedder.embed.return_value = [1.0, 0.0, 0.0]
    rag = RAGRetriever(mgr, embedder)

    results = rag.retrieve("python", ["acos_experiences", "acos_skills"])

    ids = {r["id"] for r in results}
    assert ids == {"e1", "s1"}  # job_descriptions excluded by the filter
    assert all(r["collection"] in {"acos_experiences", "acos_skills"} for r in results)


def test_single_doc_type_excludes_others(tmp_path):
    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    _seed(mgr)
    embedder = MagicMock()
    embedder.embed.return_value = [1.0, 0.0, 0.0]
    rag = RAGRetriever(mgr, embedder)

    results = rag.retrieve("python", ["acos_job_descriptions"])
    assert {r["id"] for r in results} == {"j1"}
