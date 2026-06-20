from __future__ import annotations

import logging

from sqlalchemy.orm import Session

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

    def index_all(self, session: Session) -> int:
        """Re-embed all ingested documents stored in the database.

        Queries Document rows with status 'complete' and non-empty raw_text in
        metadata_json, then upserts each into the 'acos_documents' collection.
        Returns the count of documents indexed.
        """
        from backend.models.document import Document

        rows = session.query(Document).filter(Document.ingestion_status == "complete").all()
        count = 0
        for doc in rows:
            text: str = (doc.metadata_json or {}).get("raw_text", "")
            if not text:
                continue
            self.index_document(
                collection_name="acos_documents",
                doc_id=str(doc.id),
                text=text,
                metadata={"source": doc.original_path or "", "confidence": "verified"},
            )
            count += 1
        return count
