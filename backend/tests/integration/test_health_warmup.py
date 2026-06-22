"""TDD for /health/warmup (Phase 11.3).

Lazy Chroma init must not hide connection errors until a user request. The
warmup probe forces ChromaManager to materialize its client + collections so
failures surface on demand.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_health_warmup_triggers_chroma_init(client):
    with patch("backend.rag.chroma_client.ChromaManager") as M:
        inst = MagicMock()
        M.return_value = inst
        r = client.get("/api/v1/health/warmup")
    assert r.status_code == 200
    body = r.json()
    assert body["warmed"] is True
    assert body["chroma"] == "ok"
    inst.init_all_collections.assert_called_once()


def test_health_warmup_reports_failure(client):
    with patch("backend.rag.chroma_client.ChromaManager") as M:
        M.return_value.init_all_collections.side_effect = RuntimeError("boom")
        r = client.get("/api/v1/health/warmup")
    assert r.status_code == 503
    body = r.json()
    assert body["warmed"] is False
    assert "boom" in body["chroma"]
