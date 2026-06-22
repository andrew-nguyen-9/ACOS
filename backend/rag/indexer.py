from __future__ import annotations

import hashlib
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


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

    def index_all(self, session: Session, only_changed: bool = False) -> int:
        """Re-embed ingested documents stored in the database.

        Queries Document rows with status 'complete' and non-empty raw_text in
        metadata_json, then upserts each into the 'acos_documents' collection.
        Stores a content_hash in the metadata. When ``only_changed`` is True,
        documents whose content_hash already matches what is stored in Chroma
        are skipped (no embed call). Returns the count of documents (re)embedded.
        """
        from backend.models.document import Document

        rows = session.query(Document).filter(Document.ingestion_status == "complete").all()
        candidates = [
            (str(doc.id), text, doc.original_path or "")
            for doc in rows
            if (text := (doc.metadata_json or {}).get("raw_text", ""))
        ]

        stored_hashes: dict[str, str] = {}
        if only_changed and candidates:
            existing = self._chroma.get(
                collection="acos_documents", ids=[c[0] for c in candidates]
            )
            # content_hash hashes the *embed input* (raw_text); distinct from
            # Document.checksum_sha256 which hashes the original file bytes.
            for _id, meta in zip(existing.get("ids") or [], existing.get("metadatas") or []):
                if meta:
                    stored_hashes[_id] = meta.get("content_hash", "")

        count = 0
        for doc_id, text, source in candidates:
            content_hash = _content_hash(text)
            if only_changed and stored_hashes.get(doc_id) == content_hash:
                continue
            self.index_document(
                collection_name="acos_documents",
                doc_id=doc_id,
                text=text,
                metadata={
                    "source": source,
                    "confidence": "verified",
                    "content_hash": content_hash,
                },
            )
            count += 1
        return count
