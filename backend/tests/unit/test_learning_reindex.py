from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_reindex_endpoint_returns_ok(client):
    with patch("backend.api.v1.routes.learning.RAGIndexer") as mock_cls:
        mock_indexer = MagicMock()
        mock_indexer.index_all.return_value = 42
        mock_cls.return_value = mock_indexer
        resp = client.post("/api/v1/learning/reindex")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["indexed"] == 42
