from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.35


class RAGRetriever:
    def __init__(self, chroma_manager, embedder) -> None:
        self._chroma = chroma_manager
        self._embedder = embedder

    def retrieve(
        self, query: str, collections: list[str], top_k: int = 10
    ) -> list[dict]:
        query_embedding = self._embedder.embed(query)
        all_results: list[dict] = []

        for collection_name in collections:
            try:
                raw = self._chroma.query(
                    collection=collection_name,
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                )
                ids = raw.get("ids", [[]])[0]
                docs = raw.get("documents", [[]])[0]
                metas = raw.get("metadatas", [[]])[0]
                distances = raw.get("distances", [[]])[0]

                for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
                    semantic_score = max(0.0, 1.0 - dist)
                    if semantic_score >= MIN_SIMILARITY:
                        all_results.append({
                            "id": doc_id,
                            "text": text,
                            "metadata": meta or {},
                            "semantic_score": semantic_score,
                            "collection": collection_name,
                        })
            except Exception as exc:
                logger.warning(
                    "retrieve: collection %s failed: %s", collection_name, exc
                )

        return all_results
