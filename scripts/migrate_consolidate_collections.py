"""Phase 12.6 one-time migration: consolidate 10 Chroma collections into one.

Re-homes every legacy collection's vectors into ``acos_documents``, tagging each
record with a ``doc_type`` metadata field (== the legacy collection name) so the
retriever can partition with ``where={"doc_type": {"$in": [...]}}``. Vectors,
documents and metadata are COPIED — nothing is re-embedded (spec §3).

Why a standalone script, not an Alembic revision: ChromaDB is not part of the
SQLAlchemy metadata. An Alembic ``upgrade()`` runs with only a relational
connection and fires on every fresh/test DB; opening a vector store there would
couple schema migrations to Chroma and run on databases that have no vectors.
This script is idempotent and safe to re-run:

    PYTHONPATH=. .venv/bin/python -m scripts.migrate_consolidate_collections

Idempotency: vectors are upserted by id (re-run = no duplication), and each
legacy collection is deleted only after its records are copied, so a second run
finds nothing left to move.
"""
from __future__ import annotations

import logging

from backend.rag.collections import DEFAULT_DOC_TYPE, DOCUMENTS, LEGACY_COLLECTION_NAMES

logger = logging.getLogger(__name__)


def _backfill_doctype(manager) -> int:
    """Tag any acos_documents rows that predate doc_type (e.g. old index_all runs)."""
    data = manager.export_all(DOCUMENTS)
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    # embeddings come back as a numpy array — guard with `is None`, not truthiness.
    embs = data.get("embeddings")
    embs = embs if embs is not None else []
    metas = data.get("metadatas") or []

    b_ids, b_docs, b_embs, b_metas = [], [], [], []
    for _id, doc, emb, meta in zip(ids, docs, embs, metas):
        meta = meta or {}
        if not meta.get("doc_type"):
            b_ids.append(_id)
            b_docs.append(doc)
            b_embs.append(list(emb))
            b_metas.append({**meta, "doc_type": DEFAULT_DOC_TYPE})
    if b_ids:
        manager.upsert(DOCUMENTS, ids=b_ids, documents=b_docs, embeddings=b_embs, metadatas=b_metas)
    return len(b_ids)


def consolidate_collections(manager) -> dict:
    """Move legacy collections into DOCUMENTS and backfill doc_type. Returns counts."""
    existing = set(manager.list_collection_names())
    moved = 0
    for legacy in LEGACY_COLLECTION_NAMES:
        if legacy == DOCUMENTS or legacy not in existing:
            continue
        data = manager.export_all(legacy)
        ids = data.get("ids") or []
        if not ids:
            manager.delete_collection(legacy)
            continue
        metas = data.get("metadatas") or [{} for _ in ids]
        embs = data.get("embeddings")
        embs = embs if embs is not None else []
        manager.upsert(
            DOCUMENTS,
            ids=ids,
            documents=data.get("documents") or ["" for _ in ids],
            embeddings=[list(e) for e in embs],
            metadatas=[{**(m or {}), "doc_type": legacy} for m in metas],
        )
        manager.delete_collection(legacy)
        moved += len(ids)
        logger.info("migrated %d vectors from %s -> %s", len(ids), legacy, DOCUMENTS)

    backfilled = _backfill_doctype(manager)
    return {"moved": moved, "backfilled": backfilled}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from backend.config import get_settings
    from backend.rag.chroma_client import get_chroma_manager

    manager = get_chroma_manager(get_settings().chroma_db_path)
    result = consolidate_collections(manager)
    logger.info("consolidation complete: %s", result)


if __name__ == "__main__":
    main()
