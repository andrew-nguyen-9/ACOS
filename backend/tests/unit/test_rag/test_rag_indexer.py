from unittest.mock import MagicMock
import pytest
from backend.rag.collections import DOCUMENTS, DEFAULT_DOC_TYPE
from backend.rag.indexer import RAGIndexer


@pytest.fixture
def mock_chroma():
    return MagicMock()


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
