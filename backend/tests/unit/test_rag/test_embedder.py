from unittest.mock import MagicMock

from backend.rag.embedder import Embedder


def _make_embedder() -> tuple[Embedder, MagicMock]:
    mock_client = MagicMock()
    mock_client.embed.return_value = [0.1] * 768
    mock_client.embed_batch.side_effect = lambda model, texts: [[0.1] * 768 for _ in texts]
    return Embedder(ollama_client=mock_client, model="nomic-embed-text"), mock_client


def test_embed_calls_client_with_correct_args():
    embedder, mock_client = _make_embedder()
    result = embedder.embed("some text")
    mock_client.embed.assert_called_once_with(model="nomic-embed-text", text="some text")
    assert result == [0.1] * 768


def test_embed_batch_returns_one_vector_per_text():
    embedder, mock_client = _make_embedder()
    texts = ["a", "b", "c"]
    results = embedder.embed_batch(texts)
    assert len(results) == 3
    # one batched call (≤128), not one call per text
    assert mock_client.embed_batch.call_count == 1


def test_embed_batch_empty_returns_empty():
    embedder, _ = _make_embedder()
    assert embedder.embed_batch([]) == []
