from unittest.mock import MagicMock, call
import pytest
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


def test_index_document_calls_upsert(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    mock_chroma.get_or_create_collection.return_value = MagicMock()
    indexer.index_document("acos_skills", "id1", "Python programming", {"confidence": "verified"})
    mock_chroma.upsert.assert_called_once()
    args = mock_chroma.upsert.call_args
    assert args.kwargs["ids"] == ["id1"] or args[1]["ids"] == ["id1"]


def test_index_batch_embeds_all_texts(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    mock_chroma.get_or_create_collection.return_value = MagicMock()
    items = [
        {"id": "a", "text": "Python", "metadata": {}},
        {"id": "b", "text": "SQL", "metadata": {}},
    ]
    indexer.index_batch("acos_skills", items)
    mock_embedder.embed_batch.assert_called_once_with(["Python", "SQL"])
    mock_chroma.upsert.assert_called_once()


def test_delete_document(mock_chroma, mock_embedder):
    indexer = RAGIndexer(mock_chroma, mock_embedder)
    mock_chroma.get_or_create_collection.return_value = MagicMock()
    indexer.delete_document("acos_skills", "id1")
    mock_chroma.delete.assert_called_once()
