from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.rag.collections import DOCUMENTS, DEFAULT_DOC_TYPE
from backend.rag.indexer import RAGIndexer
from backend.services.rag import lexical


@pytest.fixture
def mock_chroma():
    return MagicMock()


@pytest.fixture
def fts_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    lexical.ensure_fts5(session)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def mock_embedder():
    e = MagicMock()
    e.embed.return_value = [0.1] * 768
    e.embed_batch.return_value = [[0.1] * 768, [0.2] * 768]
    return e


def test_index_document_writes_to_documents_with_doc_type(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    indexer.index_document("id1", "Python programming", {"confidence": "verified"},
                           doc_type="acos_skills")
    mock_chroma.upsert.assert_called_once()
    kwargs = mock_chroma.upsert.call_args.kwargs
    assert kwargs["collection"] == DOCUMENTS
    assert kwargs["ids"] == ["id1"]
    assert kwargs["metadatas"][0]["doc_type"] == "acos_skills"
    assert kwargs["metadatas"][0]["confidence"] == "verified"


def test_index_document_defaults_doc_type(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    indexer.index_document("id1", "text", {})
    assert mock_chroma.upsert.call_args.kwargs["metadatas"][0]["doc_type"] == DEFAULT_DOC_TYPE


def test_index_batch_embeds_all_and_tags_doc_type(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    items = [
        {"id": "a", "text": "Python", "metadata": {}},
        {"id": "b", "text": "SQL", "metadata": {}},
    ]
    indexer.index_batch(items, doc_type="acos_skills")
    mock_embedder.embed_batch.assert_called_once_with(["Python", "SQL"])
    kwargs = mock_chroma.upsert.call_args.kwargs
    assert kwargs["collection"] == DOCUMENTS
    assert [m["doc_type"] for m in kwargs["metadatas"]] == ["acos_skills", "acos_skills"]


def test_delete_document(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    indexer.delete_document("id1")
    mock_chroma.delete.assert_called_once_with(collection=DOCUMENTS, ids=["id1"])


# --- FTS5 lexical sync (Phase 12.7): indexer mirrors every Chroma write ---


def test_index_document_mirrors_to_fts5(mock_chroma, mock_embedder, fts_session):
    indexer = RAGIndexer(mock_chroma, mock_embedder, session=fts_session)
    indexer.index_document("id1", "python async performance", {}, doc_type="acos_experiences")
    fts_session.commit()
    hits = lexical.search(fts_session, "python performance", ["acos_experiences"], k=5)
    assert [h["id"] for h in hits] == ["id1"]


def test_index_batch_mirrors_to_fts5(mock_chroma, mock_embedder, fts_session):
    indexer = RAGIndexer(mock_chroma, mock_embedder, session=fts_session)
    indexer.index_batch(
        [
            {"id": "a", "text": "python data pipeline", "metadata": {}},
            {"id": "b", "text": "react design system", "metadata": {}},
        ],
        doc_type="acos_projects",
    )
    fts_session.commit()
    assert [h["id"] for h in lexical.search(fts_session, "python pipeline", ["acos_projects"], k=5)] == ["a"]
    assert [h["id"] for h in lexical.search(fts_session, "react design", ["acos_projects"], k=5)] == ["b"]


def test_delete_document_removes_from_fts5(mock_chroma, mock_embedder, fts_session):
    indexer = RAGIndexer(mock_chroma, mock_embedder, session=fts_session)
    indexer.index_document("id1", "python async performance", {}, doc_type="acos_experiences")
    fts_session.commit()
    indexer.delete_document("id1")
    fts_session.commit()
    assert lexical.search(fts_session, "python performance", ["acos_experiences"], k=5) == []


def test_no_session_skips_fts5_sync(mock_chroma, mock_embedder):
    """Backward-compat: callers without a DB session stay Chroma-only, no error."""
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    indexer.index_document("id1", "python", {}, doc_type="acos_experiences")  # must not raise
    mock_chroma.upsert.assert_called_once()
