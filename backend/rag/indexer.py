from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class RAGIndexer:
    def __init__(self, chroma_manager, embedder) -> None:
        self._chroma = chroma_manager
        self._embedder = embedder

    def index_document(
        self, collection_name: str, doc_id: str, text: str, metadata: dict
    ) -> None:
        embedding = self._embedder.embed(text)
        self._chroma.upsert(
            collection=collection_name,
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.debug("indexed document %s in %s", doc_id, collection_name)

    def index_batch(self, collection_name: str, items: list[dict]) -> None:
        if not items:
            return
        texts = [item["text"] for item in items]
        embeddings = self._embedder.embed_batch(texts)
        self._chroma.upsert(
            collection=collection_name,
            ids=[item["id"] for item in items],
            documents=texts,
            embeddings=embeddings,
            metadatas=[item["metadata"] for item in items],
        )
        logger.debug("indexed batch of %d in %s", len(items), collection_name)

    def delete_document(self, collection_name: str, doc_id: str) -> None:
        self._chroma.delete(collection=collection_name, ids=[doc_id])
