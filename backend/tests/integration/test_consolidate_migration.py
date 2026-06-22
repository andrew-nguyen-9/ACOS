"""Phase 12.6 AC2 — one-time migration re-homes legacy collections into one.

Real ChromaDB (tmp dir). Copies vectors+docs+metadata (NO re-embedding), tags
doc_type, backfills untagged acos_documents rows, and is idempotent on re-run.
"""
from __future__ import annotations

from backend.rag.chroma_client import ChromaManager
from backend.rag.collections import DEFAULT_DOC_TYPE, DOCUMENTS
from scripts.migrate_consolidate_collections import consolidate_collections


def _seed_legacy(mgr: ChromaManager) -> None:
    mgr.add(
        "acos_experiences",
        ids=["e1"],
        documents=["led migration"],
        embeddings=[[1.0, 0.0, 0.0]],
        metadatas=[{"confidence_level": "verified"}],
    )
    mgr.add(
        "acos_skills",
        ids=["s1"],
        documents=["python"],
        embeddings=[[0.0, 1.0, 0.0]],
        metadatas=[{"confidence_level": "strong_inference"}],
    )
    # pre-existing acos_documents row from index_all, lacking doc_type
    mgr.add(
        DOCUMENTS,
        ids=["d1"],
        documents=["generic doc"],
        embeddings=[[0.0, 0.0, 1.0]],
        metadatas=[{"source": "x"}],
    )


def test_migration_rehomes_and_tags_doc_type(tmp_path):
    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    _seed_legacy(mgr)

    result = consolidate_collections(mgr)

    assert mgr.count(DOCUMENTS) == 3
    assert mgr.get(DOCUMENTS, ids=["e1"])["metadatas"][0]["doc_type"] == "acos_experiences"
    assert mgr.get(DOCUMENTS, ids=["s1"])["metadatas"][0]["doc_type"] == "acos_skills"
    # untagged pre-existing row backfilled to the default doc_type
    assert mgr.get(DOCUMENTS, ids=["d1"])["metadatas"][0]["doc_type"] == DEFAULT_DOC_TYPE
    assert result["moved"] == 2
    assert result["backfilled"] == 1
    # legacy collections removed after copy
    assert "acos_experiences" not in mgr.list_collection_names()


def test_migration_preserves_embeddings_without_reembedding(tmp_path):
    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    _seed_legacy(mgr)
    consolidate_collections(mgr)
    got = mgr.export_all(DOCUMENTS)
    by_id = dict(zip(got["ids"], got["embeddings"]))
    assert list(by_id["e1"]) == [1.0, 0.0, 0.0]  # exact vector carried over


def test_migration_idempotent(tmp_path):
    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    _seed_legacy(mgr)
    consolidate_collections(mgr)
    second = consolidate_collections(mgr)
    assert mgr.count(DOCUMENTS) == 3  # no duplication
    assert second["moved"] == 0  # legacy already consumed
    assert second["backfilled"] == 0
