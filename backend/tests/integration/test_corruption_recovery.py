"""Phase 11.4 — corrupt DB on startup → safe read-only mode, not a crash.

The startup probe is the cheap ``PRAGMA quick_check`` (not full integrity_check,
to protect cold-start budget). On failure the app enters READONLY_RECOVERY:
mutating endpoints return 503, but /recovery/status and /backup/restore stay open.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models.base import Base
from backend.models.system_config import SystemConfig
from backend.recovery import (
    RECOVERY,
    ReadonlyRecoveryMiddleware,
    check_interrupted_restore,
    maybe_enter_recovery,
    probe_integrity,
)
from backend.services.backup.restore import SENTINEL_NAME


@pytest.fixture(autouse=True)
def _reset_recovery():
    RECOVERY.clear()
    yield
    RECOVERY.clear()


def _healthy_session(db_path: Path) -> Session:
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(SystemConfig(key="k", value="v"))
        s.commit()
    return Session(eng)


def _corrupt_session(db_path: Path) -> Session:
    # First make a valid DB, then overwrite its header with garbage.
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    eng.dispose()
    with open(db_path, "r+b") as f:
        f.write(b"this is not a sqlite header at all, totally corrupt")
    bad = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return Session(bad)


def test_probe_passes_on_healthy_db(tmp_path):
    assert probe_integrity(_healthy_session(tmp_path / "ok.db")) is True


def test_probe_fails_on_corrupt_db(tmp_path):
    assert probe_integrity(_corrupt_session(tmp_path / "bad.db")) is False


def test_maybe_enter_recovery_sets_flag_on_corruption(tmp_path):
    maybe_enter_recovery(_corrupt_session(tmp_path / "bad.db"))
    assert RECOVERY.readonly is True
    assert RECOVERY.reason


def test_maybe_enter_recovery_stays_clear_when_healthy(tmp_path):
    maybe_enter_recovery(_healthy_session(tmp_path / "ok.db"))
    assert RECOVERY.readonly is False


def test_interrupted_restore_sentinel_enters_recovery(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    (backups / SENTINEL_NAME).write_text('{"pre_restore": "snap-xyz"}')
    assert check_interrupted_restore(backups) is True
    assert RECOVERY.readonly is True
    assert "snap-xyz" in RECOVERY.reason


def test_no_sentinel_no_recovery(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    assert check_interrupted_restore(backups) is False
    assert RECOVERY.readonly is False


def _app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ReadonlyRecoveryMiddleware)

    @app.post("/api/v1/things")
    def make_thing():
        return {"ok": True}

    @app.get("/api/v1/things")
    def get_thing():
        return {"ok": True}

    @app.post("/api/v1/backup/restore")
    def do_restore():
        return {"restored": True}

    @app.get("/api/v1/recovery/status")
    def recovery_status():
        return {"readonly": RECOVERY.readonly}

    return app


def test_mutating_route_blocked_in_readonly():
    client = TestClient(_app_with_middleware())
    RECOVERY.enter("corrupt")
    assert client.post("/api/v1/things").status_code == 503


def test_reads_and_restore_allowed_in_readonly():
    client = TestClient(_app_with_middleware())
    RECOVERY.enter("corrupt")
    assert client.get("/api/v1/things").status_code == 200          # reads fine
    assert client.post("/api/v1/backup/restore").status_code == 200  # restore exempt
    assert client.get("/api/v1/recovery/status").status_code == 200


def test_mutations_allowed_when_not_readonly():
    client = TestClient(_app_with_middleware())
    assert client.post("/api/v1/things").status_code == 200
