from __future__ import annotations

import hashlib
import logging

from sqlalchemy.orm import Session

from backend.rag.collections import DEFAULT_DOC_TYPE, DOCUMENTS
from backend.services.rag import lexical

logger = logging.getLogger(__name__)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class RAGIndexer:
    def __init__(self, chroma_manager, embedder, session: Session | None = None) -> None:
        self._chroma = chroma_manager
        self._embedder = embedder
        # When set, the indexer mirrors every corpus write into the FTS5 lexical
        # table (12.7). Chroma + FTS5 stay in sync because this is the single
        # write chokepoint. None → Chroma-only (callers that don't need lexical).
        self._session = session

    def index_document(
        self, doc_id: str, text: str, metadata: dict, *, doc_type: str = DEFAULT_DOC_TYPE
    ) -> None:
        """Embed and upsert one document into the consolidated collection.

        ``doc_type`` is written into metadata so the retriever can partition by
        ``where={"doc_type": ...}`` — physical collection is always DOCUMENTS.
        """
        embedding = self._embedder.embed(text)
        self._chroma.upsert(
            collection=DOCUMENTS,
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{**metadata, "doc_type": doc_type}],
        )
        if self._session is not None:
            lexical.upsert(self._session, doc_id, text, doc_type)
        logger.debug("indexed document %s as doc_type=%s", doc_id, doc_type)

    def index_batch(
        self, items: list[dict], *, doc_type: str = DEFAULT_DOC_TYPE
    ) -> None:
        if not items:
            return
        texts = [item["text"] for item in items]
        embeddings = self._embedder.embed_batch(texts)
        self._chroma.upsert(
            collection=DOCUMENTS,
            ids=[item["id"] for item in items],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{**item["metadata"], "doc_type": doc_type} for item in items],
        )
        if self._session is not None:
            for item in items:
                lexical.upsert(self._session, item["id"], item["text"], doc_type)
        logger.debug("indexed batch of %d as doc_type=%s", len(items), doc_type)

    def delete_document(self, doc_id: str) -> None:
        self._chroma.delete(collection=DOCUMENTS, ids=[doc_id])
        if self._session is not None:
            lexical.delete(self._session, doc_id)

    def index_all(self, session: Session, only_changed: bool = False) -> int:
        """Re-embed ingested documents stored in the database.

        Queries Document rows with status 'complete' and non-empty raw_text in
        metadata_json, then upserts each into the consolidated collection tagged
        with the default doc_type. Stores a content_hash in the metadata. When
        ``only_changed`` is True, documents whose content_hash already matches what
        is stored in Chroma are skipped (no embed call). Returns the count of
        documents (re)embedded.
        """
        from backend.models.document import Document

        # index_document mirrors to FTS5 via self._session; bind it to the working
        # sync session so a reseed rebuilds the lexical index alongside Chroma.
        self._session = session

        rows = session.query(Document).filter(Document.ingestion_status == "complete").all()
        candidates = [
            (str(doc.id), text, doc.original_path or "")
            for doc in rows
            if (text := (doc.metadata_json or {}).get("raw_text", ""))
        ]

        stored_hashes: dict[str, str] = {}
        if only_changed and candidates:
            existing = self._chroma.get(
                collection=DOCUMENTS, ids=[c[0] for c in candidates]
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
