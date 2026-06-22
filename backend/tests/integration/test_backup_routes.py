"""Phase 11.4 — backup API: snapshot, list, restore, recovery status."""
from __future__ import annotations

import sqlite3

import pytest

from backend.config import get_settings
from backend.recovery import RECOVERY


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    db = tmp_path / "acos.db"
    sqlite3.connect(db).close()  # empty valid sqlite file
    monkeypatch.setenv("ACOS_DB_PATH", str(db))
    monkeypatch.setenv("ACOS_CHROMA_PATH", str(tmp_path / "chroma"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_snapshot_then_list(client, tmp_settings):
    r = client.post("/api/v1/backup/snapshot", json={"full": True})
    assert r.status_code == 200
    snap_id = r.json()["id"]

    listed = client.get("/api/v1/backup/list").json()["snapshots"]
    assert any(s["id"] == snap_id for s in listed)


def test_restore_round_trip(client, tmp_settings):
    snap_id = client.post("/api/v1/backup/snapshot", json={"full": True}).json()["id"]
    r = client.post("/api/v1/backup/restore", json={"snapshot_id": snap_id})
    assert r.status_code == 200
    body = r.json()
    assert body["integrity_ok"] is True
    assert body["pre_restore_snapshot_id"]


def test_restore_unknown_returns_404(client, tmp_settings):
    r = client.post("/api/v1/backup/restore", json={"snapshot_id": "../escape"})
    assert r.status_code == 404


def test_recovery_status_reports_flag(client):
    RECOVERY.clear()
    assert client.get("/api/v1/recovery/status").json()["readonly"] is False
    RECOVERY.enter("test corruption")
    try:
        body = client.get("/api/v1/recovery/status").json()
        assert body["readonly"] is True
        assert body["reason"] == "test corruption"
    finally:
        RECOVERY.clear()
