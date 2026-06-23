from __future__ import annotations

import logging

from backend.rag.collections import DOCUMENTS

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.35


class RAGRetriever:
    def __init__(self, chroma_manager, embedder) -> None:
        self._chroma = chroma_manager
        self._embedder = embedder

    def retrieve(
        self, query: str, doc_types: list[str], top_k: int = 10
    ) -> list[dict]:
        """Retrieve from the single consolidated collection, filtered by doc_type.

        One physical query over ``acos_documents`` with ``where={"doc_type":
        {"$in": doc_types}}`` replaces the old per-collection loop. ``n_results``
        scales with the partition count so a multi-type intent keeps the recall it
        had when each partition was queried separately.
        """
        if not doc_types:
            return []
        query_embedding = self._embedder.embed(query)
        n_results = top_k * len(doc_types)
        try:
            raw = self._chroma.query(
                collection=DOCUMENTS,
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"doc_type": {"$in": doc_types}},
            )
        except Exception as exc:
            logger.warning("retrieve: query failed: %s", exc)
            return []

        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results: list[dict] = []
        for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
            semantic_score = max(0.0, 1.0 - dist)
            if semantic_score >= MIN_SIMILARITY:
                meta = meta or {}
                results.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": meta,
                    "semantic_score": semantic_score,
                    "collection": meta.get("doc_type", DOCUMENTS),
                })
        return results
