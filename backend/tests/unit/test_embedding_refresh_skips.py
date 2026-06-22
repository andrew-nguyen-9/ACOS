"""Embedding refresh skips unchanged content via content-hash (Phase 11.3).

`RAGIndexer.index_all(session, only_changed=True)` must not re-embed documents
whose content hash already matches what is stored in Chroma. Changed content is
re-embedded.
"""
from __future__ import annotations

from backend.models.document import Document
from backend.rag.indexer import RAGIndexer


class _FakeChroma:
    """Records upserts and serves them back via get(), keyed by id."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}  # id -> metadata
        self.upsert_calls = 0

    def upsert(self, collection, ids, documents, embeddings, metadatas, tenant_id=None):
        self.upsert_calls += 1
        for i, _id in enumerate(ids):
            self.store[_id] = metadatas[i]

    def get(self, collection, ids):
        metadatas = [self.store.get(i) for i in ids]
        return {"ids": ids, "metadatas": metadatas}


class _CountingEmbedder:
    def __init__(self) -> None:
        self.embed_calls = 0

    def embed(self, text):
        self.embed_calls += 1
        return [0.0, 1.0, 2.0]

    def embed_batch(self, texts):
        self.embed_calls += len(texts)
        return [[0.0, 1.0, 2.0] for _ in texts]


def _add_doc(session, raw_text: str) -> Document:
    doc = Document(
        filename="r.txt",
        original_path="/x/r.txt",
        file_type="txt",
        source_type="resume",
        ingestion_status="complete",
        metadata_json={"raw_text": raw_text},
    )
    session.add(doc)
    session.commit()
    return doc


def test_first_index_embeds_all(test_session):
    _add_doc(test_session, "alpha")
    _add_doc(test_session, "beta")
    emb = _CountingEmbedder()
    idx = RAGIndexer(_FakeChroma(), emb)

    count = idx.index_all(test_session)

    assert count == 2
    assert emb.embed_calls == 2


def test_only_changed_skips_unchanged(test_session):
    _add_doc(test_session, "alpha")
    _add_doc(test_session, "beta")
    chroma = _FakeChroma()
    emb = _CountingEmbedder()
    idx = RAGIndexer(chroma, emb)
    idx.index_all(test_session)  # populate hashes
    emb.embed_calls = 0

    count = idx.index_all(test_session, only_changed=True)

    assert count == 0
    assert emb.embed_calls == 0


def test_only_changed_reembeds_changed(test_session):
    d1 = _add_doc(test_session, "alpha")
    _add_doc(test_session, "beta")
    chroma = _FakeChroma()
    emb = _CountingEmbedder()
    idx = RAGIndexer(chroma, emb)
    idx.index_all(test_session)
    emb.embed_calls = 0

    d1.metadata_json = {"raw_text": "alpha-edited"}
    test_session.commit()
    count = idx.index_all(test_session, only_changed=True)

    assert count == 1
    assert emb.embed_calls == 1
