"""Phase 11.4 — maintenance API: generate, list, approve, execute, audit."""
from __future__ import annotations

import sqlite3

import pytest

from backend.config import get_settings
from backend.services.observability.metrics import MetricsStore


def _seed_reindex_signal(session):
    store = MetricsStore(session)
    for _ in range(5):
        store.record("retrieval_quality", 0.9)
    for _ in range(5):
        store.record("retrieval_quality", 0.4)
    session.flush()


def test_generate_then_list_suggestions(client, test_session):
    _seed_reindex_signal(test_session)
    r = client.post("/api/v1/maintenance/generate")
    assert r.status_code == 200
    assert r.json()["created"] >= 1

    listed = client.get("/api/v1/maintenance/suggestions").json()["suggestions"]
    assert any(s["type"] == "reindex" for s in listed)


def test_approve_suggestion(client, test_session):
    _seed_reindex_signal(test_session)
    sid = client.post("/api/v1/maintenance/generate").json()["suggestion_ids"][0]
    r = client.post("/api/v1/maintenance/approve", json={"suggestion_id": sid})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_approve_unknown_returns_404(client):
    r = client.post("/api/v1/maintenance/approve", json={"suggestion_id": "nope"})
    assert r.status_code == 404


def test_execute_unapproved_returns_409(client, test_session):
    _seed_reindex_signal(test_session)
    sid = client.post("/api/v1/maintenance/generate").json()["suggestion_ids"][0]
    r = client.post("/api/v1/maintenance/execute", json={"suggestion_id": sid})
    assert r.status_code == 409  # not approved


def test_list_suggestions_filtered_by_status(client, test_session):
    _seed_reindex_signal(test_session)
    client.post("/api/v1/maintenance/generate")
    suggested = client.get("/api/v1/maintenance/suggestions?status=suggested").json()["suggestions"]
    assert suggested and all(s["status"] == "suggested" for s in suggested)
    assert client.get("/api/v1/maintenance/suggestions?status=executed").json()["suggestions"] == []


def test_dismiss_suggestion(client, test_session):
    _seed_reindex_signal(test_session)
    sid = client.post("/api/v1/maintenance/generate").json()["suggestion_ids"][0]
    r = client.post("/api/v1/maintenance/dismiss", json={"suggestion_id": sid})
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"


def test_dismiss_unknown_returns_404(client):
    r = client.post("/api/v1/maintenance/dismiss", json={"suggestion_id": "nope"})
    assert r.status_code == 404


def test_execute_unknown_returns_404(client):
    r = client.post("/api/v1/maintenance/execute", json={"suggestion_id": "nope"})
    assert r.status_code == 404


def test_audit_lists_events(client, test_session):
    _seed_reindex_signal(test_session)
    client.post("/api/v1/maintenance/generate")
    audit = client.get("/api/v1/maintenance/audit").json()["audit"]
    assert any(a["event"] == "suggested" for a in audit)


def test_execute_model_switch_round_trip(client, test_session, tmp_path, monkeypatch):
    # Point backup paths at a temp dir so execute's pre-snapshot doesn't touch real fs.
    db = tmp_path / "acos.db"
    sqlite3.connect(db).close()
    monkeypatch.setenv("ACOS_DB_PATH", str(db))
    monkeypatch.setenv("ACOS_CHROMA_PATH", str(tmp_path / "chroma"))
    get_settings.cache_clear()
    try:
        from backend.repositories.system_config import SystemConfigRepository
        from backend.models.maintenance import MaintenanceSuggestion
        import json

        SystemConfigRepository(test_session).set_value("default_model", "qwen3:8b")
        s = MaintenanceSuggestion(
            type="model_switch", reason="t", payload_json=json.dumps({"to_model": "qwen3:4b"})
        )
        test_session.add(s)
        test_session.flush()

        client.post("/api/v1/maintenance/approve", json={"suggestion_id": s.id})
        r = client.post("/api/v1/maintenance/execute", json={"suggestion_id": s.id})
        assert r.status_code == 200
        assert r.json()["status"] == "executed"
        assert SystemConfigRepository(test_session).get_value("default_model") == "qwen3:4b"
    finally:
        get_settings.cache_clear()
