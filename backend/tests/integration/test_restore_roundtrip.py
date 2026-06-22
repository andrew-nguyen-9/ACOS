"""Phase 11.4 — restore is reversible (snapshot-current-first) and atomic.

Restore assumes the DB is otherwise idle (the app is in READONLY_RECOVERY mode
or shut down); it manages its own short-lived connections so the caller does not
hold the file open during the swap.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.models.base import Base
from backend.models.system_config import SystemConfig
from backend.services.backup.snapshot import snapshot, list_snapshots
from backend.services.backup.restore import restore, RestoreError


def _engine(db_path: Path):
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return eng


def _set_config(db_path: Path, key: str, value: str) -> None:
    eng = _engine(db_path)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        row = s.get(SystemConfig, key)
        if row is None:
            s.add(SystemConfig(key=key, value=value))
        else:
            row.value = value
        s.commit()
    eng.dispose()


def _read_config(db_path: Path, key: str) -> str | None:
    eng = _engine(db_path)
    with Session(eng) as s:
        row = s.get(SystemConfig, key)
        val = row.value if row else None
    eng.dispose()
    return val


def test_db_state_round_trips_through_snapshot_and_restore(tmp_path):
    db = tmp_path / "acos.db"
    backups = tmp_path / "backups"
    nochroma = str(tmp_path / "nochroma")

    _set_config(db, "marker", "A")  # state A
    eng = _engine(db)
    with Session(eng) as s:
        snap_a = snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    eng.dispose()

    _set_config(db, "marker", "B")  # mutate to state B
    assert _read_config(db, "marker") == "B"

    result = restore(snap_a.id, backups_dir=backups, db_path=str(db), chroma_path=nochroma)

    assert _read_config(db, "marker") == "A"          # restored
    assert result.integrity_ok is True                 # validated post-restore
    # snapshot-current-first ran: a pre-restore restore point exists and is newer.
    assert result.pre_restore_snapshot_id != snap_a.id
    ids = {m.id for m in list_snapshots(backups)}
    assert result.pre_restore_snapshot_id in ids


def test_restore_swaps_chroma_directory(tmp_path):
    db = tmp_path / "acos.db"
    chroma = tmp_path / "chroma"
    backups = tmp_path / "backups"
    _set_config(db, "marker", "A")
    chroma.mkdir()
    (chroma / "store.bin").write_text("A-vectors")

    eng = _engine(db)
    with Session(eng) as s:
        snap_a = snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    eng.dispose()

    (chroma / "store.bin").write_text("B-vectors")  # mutate store
    restore(snap_a.id, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))

    assert (chroma / "store.bin").read_text() == "A-vectors"


def test_incremental_restore_resolves_chroma_from_full(tmp_path):
    # Full snapshot holds Chroma "A"; incremental skips it (unchanged). Restoring
    # the incremental must still bring Chroma back to "A" (resolved from the full),
    # not leave the live "B" store paired with the restored DB.
    db = tmp_path / "acos.db"
    chroma = tmp_path / "chroma"
    backups = tmp_path / "backups"
    _set_config(db, "marker", "A")
    chroma.mkdir()
    (chroma / "store.bin").write_text("A-vectors")

    eng = _engine(db)
    with Session(eng) as s:
        snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    eng.dispose()

    eng = _engine(db)
    with Session(eng) as s:
        incr = snapshot(s, full=False, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    eng.dispose()
    assert incr.chroma_included is False  # skipped (unchanged)

    (chroma / "store.bin").write_text("B-vectors")  # live store diverges
    restore(incr.id, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    assert (chroma / "store.bin").read_text() == "A-vectors"


def test_restore_succeeds_when_source_db_is_corrupt(tmp_path):
    # Restore exists for corruption: a corrupt *current* DB must not block it
    # (the pre-restore snapshot is best-effort and may be skipped).
    db = tmp_path / "acos.db"
    backups = tmp_path / "backups"
    nochroma = str(tmp_path / "nochroma")
    _set_config(db, "marker", "A")
    eng = _engine(db)
    with Session(eng) as s:
        snap_a = snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    eng.dispose()

    with open(db, "r+b") as f:  # corrupt the live DB
        f.write(b"garbage-not-a-sqlite-header")

    result = restore(snap_a.id, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    assert result.integrity_ok is True
    assert _read_config(db, "marker") == "A"
    assert result.pre_restore_snapshot_id is None  # corrupt source couldn't be snapshotted


def test_restore_clears_sentinel_on_success(tmp_path):
    from backend.services.backup.restore import SENTINEL_NAME

    db = tmp_path / "acos.db"
    backups = tmp_path / "backups"
    nochroma = str(tmp_path / "nochroma")
    _set_config(db, "marker", "A")
    eng = _engine(db)
    with Session(eng) as s:
        snap_a = snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    eng.dispose()
    restore(snap_a.id, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    assert not (backups / SENTINEL_NAME).exists()


def test_restore_rejects_path_traversal(tmp_path):
    db = tmp_path / "acos.db"
    _set_config(db, "marker", "A")
    with pytest.raises(RestoreError):
        restore("../../etc", backups_dir=tmp_path / "backups", db_path=str(db),
                chroma_path=str(tmp_path / "nochroma"))


def test_restore_unknown_snapshot_raises(tmp_path):
    db = tmp_path / "acos.db"
    _set_config(db, "marker", "A")
    (tmp_path / "backups").mkdir()
    with pytest.raises(RestoreError):
        restore("20990101T000000000000Z__full", backups_dir=tmp_path / "backups",
                db_path=str(db), chroma_path=str(tmp_path / "nochroma"))


def test_restored_db_passes_quick_check(tmp_path):
    db = tmp_path / "acos.db"
    backups = tmp_path / "backups"
    nochroma = str(tmp_path / "nochroma")
    _set_config(db, "marker", "A")
    eng = _engine(db)
    with Session(eng) as s:
        snap_a = snapshot(s, full=True, backups_dir=backups, db_path=str(db), chroma_path=nochroma)
    eng.dispose()
    restore(snap_a.id, backups_dir=backups, db_path=str(db), chroma_path=nochroma)

    conn = sqlite3.connect(db)
    assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    conn.close()
