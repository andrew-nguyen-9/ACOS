"""TDD for aggregated /health subsystems + /health/integrity (Phase 11.1)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_health_includes_subsystems(client):
    body = client.get("/api/v1/health").json()
    # Backward-compatible keys preserved.
    assert body["db"] == "connected"
    assert "version" in body
    # New aggregate.
    subs = body["subsystems"]
    assert subs["db"] == "ok"
    assert set(subs) >= {"db", "chroma", "ollama", "embedding", "overall"}
    assert subs["overall"] in ("ok", "degraded", "down")


def test_health_integrity_reports_checks(client):
    # Stub Chroma so the test stays hermetic (no real PersistentClient/dir).
    with patch("backend.rag.chroma_client.ChromaManager") as M:
        M.return_value = MagicMock(count=MagicMock(return_value=0))
        r = client.get("/api/v1/health/integrity")
    assert r.status_code == 200
    body = r.json()
    assert body["sqlite_integrity"] == "ok"
    assert body["foreign_key_violations"] == 0
    assert "chroma" in body
    assert "embedding" in body
