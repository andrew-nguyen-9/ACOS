"""Phase 12.6 AC3 — batched embeddings via Ollama /api/embed.

Two layers under test:
- OllamaClient.embed_batch: one POST /api/embed with input=[...] → embeddings=[[...]].
- Embedder.embed_batch: chunks into ≤128, one client call per chunk, order preserved.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from backend.rag.embedder import Embedder
from backend.services.ollama_client import OllamaClient

BASE = "http://localhost:11434"


# --- OllamaClient.embed_batch (HTTP layer) ---------------------------------


def test_client_embed_batch_hits_api_embed_with_input_array():
    texts = ["alpha", "beta", "gamma"]
    embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    client = OllamaClient(base_url=BASE, timeout=10)
    with respx.mock:
        route = respx.post(f"{BASE}/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": embeddings})
        )
        result = client.embed_batch(model="nomic-embed-text", texts=texts)

        assert result == embeddings
        assert route.call_count == 1
        body = json.loads(route.calls[0].request.content)
        assert body["model"] == "nomic-embed-text"
        assert body["input"] == texts  # array, not single `prompt`


def test_client_embed_batch_empty_makes_no_request():
    client = OllamaClient(base_url=BASE, timeout=10)
    with respx.mock:
        route = respx.post(f"{BASE}/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": []})
        )
        assert client.embed_batch(model="nomic-embed-text", texts=[]) == []
        assert route.call_count == 0


# --- Embedder.embed_batch (chunking layer) ---------------------------------


def test_embedder_batches_300_into_three_calls_preserving_order():
    """300 chunks → 3 HTTP calls (≤128 each); output order matches input order."""
    mock_client = MagicMock()
    # Each client.embed_batch call echoes a deterministic vector per input text so
    # we can assert order survives the chunk→concat round trip.
    mock_client.embed_batch.side_effect = lambda model, texts: [[float(t)] for t in texts]
    embedder = Embedder(ollama_client=mock_client, model="nomic-embed-text")

    texts = [str(i) for i in range(300)]
    results = embedder.embed_batch(texts)

    assert mock_client.embed_batch.call_count == 3  # 128 + 128 + 44
    sizes = [len(c.kwargs["texts"]) for c in mock_client.embed_batch.call_args_list]
    assert sizes == [128, 128, 44]
    assert all(s <= 128 for s in sizes)
    assert results == [[float(i)] for i in range(300)]  # order preserved end-to-end


def test_embedder_batch_empty_returns_empty():
    mock_client = MagicMock()
    embedder = Embedder(ollama_client=mock_client, model="nomic-embed-text")
    assert embedder.embed_batch([]) == []
    mock_client.embed_batch.assert_not_called()


def test_embedder_single_text_one_call():
    mock_client = MagicMock()
    mock_client.embed_batch.return_value = [[0.1, 0.2]]
    embedder = Embedder(ollama_client=mock_client, model="nomic-embed-text")
    assert embedder.embed_batch(["only"]) == [[0.1, 0.2]]
    assert mock_client.embed_batch.call_count == 1
