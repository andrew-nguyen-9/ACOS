"""Restore from a snapshot (Phase 11.4) — reversible + atomic-as-possible.

Order of operations (so a restore can itself be undone):
  1. validate the snapshot id against an allowlist (must resolve inside backups_dir)
  2. snapshot the CURRENT state first (a *best-effort* auto restore point — a
     corrupt source must still be restorable, so its failure does not abort us)
  3. write a restore-in-progress sentinel (so a crash mid-swap is detectable)
  4. swap files in: write to a temp path, fsync, then atomic ``os.replace``
  5. validate the restored DB (``PRAGMA quick_check``) and clear the sentinel

The caller must drop any live connection pool before calling (the backup route
disposes ``backend.database.engine`` first), since the DB file is replaced and
its ``-wal``/``-shm`` sidecars removed underneath open handles.

# ponytail: the DB swap and the Chroma swap are each atomic, but not atomic
# *together* — a process death between them is caught by the sentinel + startup
# reconciliation (recovery.check_interrupted_restore), not by a full WAL-style
# restore journal. Upgrade to a journal only if partial restores become real.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.services.backup.snapshot import snapshot, _DB_NAME, list_snapshots

logger = logging.getLogger(__name__)

SENTINEL_NAME = ".restore_in_progress"


class RestoreError(Exception):
    pass


@dataclass
class RestoreResult:
    restored_id: str
    pre_restore_snapshot_id: str | None
    integrity_ok: bool


def _resolve_snapshot(backups_dir: Path, snapshot_id: str) -> Path:
    """Resolve and confine snapshot_id to backups_dir (reject path traversal)."""
    backups_dir = backups_dir.resolve()
    candidate = (backups_dir / snapshot_id).resolve()
    if not candidate.is_relative_to(backups_dir):
        raise RestoreError(f"snapshot id outside backups dir: {snapshot_id!r}")
    if not (candidate / "manifest.json").is_file():
        raise RestoreError(f"snapshot not found: {snapshot_id!r}")
    return candidate


def restore(
    snapshot_id: str,
    *,
    backups_dir: str | Path,
    db_path: str,
    chroma_path: str,
    app_version: str = "0.0.0",
) -> RestoreResult:
    backups_dir = Path(backups_dir)
    snap_dir = _resolve_snapshot(backups_dir, snapshot_id)
    target_meta = json.loads((snap_dir / "manifest.json").read_text())

    # 2. Best-effort pre-restore snapshot so the restore is itself reversible.
    pre_id = _safe_pre_snapshot(backups_dir, db_path, chroma_path, app_version)

    # 3. Sentinel: lets startup detect a restore that died mid-swap.
    sentinel = backups_dir / SENTINEL_NAME
    _write_sentinel(sentinel, pre_id, snapshot_id)

    # 4. Swap DB, then Chroma. A failure after the DB swap leaves the system
    # partially restored — surface it loudly with the restore point.
    try:
        _swap_db(snap_dir / _DB_NAME, Path(db_path))
        chroma_src = _resolve_chroma_source(backups_dir, snap_dir, target_meta)
        if chroma_src is not None:
            _swap_dir(chroma_src, Path(chroma_path))
    except Exception as exc:
        raise RestoreError(
            f"restore partially applied; system may be inconsistent. "
            f"Auto restore point: {pre_id}. Cause: {exc}"
        ) from exc

    # 5. Validate and clear the sentinel.
    integrity_ok = _quick_check(Path(db_path))
    sentinel.unlink(missing_ok=True)
    return RestoreResult(
        restored_id=snapshot_id, pre_restore_snapshot_id=pre_id, integrity_ok=integrity_ok
    )


def _safe_pre_snapshot(
    backups_dir: Path, db_path: str, chroma_path: str, app_version: str
) -> str | None:
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    try:
        with Session(eng) as session:
            return snapshot(
                session, full=True, backups_dir=backups_dir,
                db_path=db_path, chroma_path=chroma_path, app_version=app_version,
            ).id
    except Exception:
        # A corrupt source can't be snapshotted — but it's exactly what the user
        # is trying to escape, so don't block the restore. Log and continue.
        logger.warning("pre-restore snapshot failed (source may be corrupt); continuing", exc_info=True)
        return None
    finally:
        eng.dispose()


def _resolve_chroma_source(backups_dir: Path, snap_dir: Path, target_meta: dict) -> Path | None:
    """The Chroma copy to restore: the target's own, else the newest snapshot
    at-or-before it that physically holds one (incremental snapshots skip an
    unchanged store, so the bytes live in an earlier full)."""
    if (snap_dir / "chroma").is_dir():
        return snap_dir / "chroma"
    target_created = target_meta.get("created_at", "")
    for m in list_snapshots(backups_dir):  # newest-first
        if m.created_at <= target_created and (Path(m.path) / "chroma").is_dir():
            return Path(m.path) / "chroma"
    return None


def _swap_db(src_db: Path, dest_db: Path) -> None:
    tmp = dest_db.with_suffix(dest_db.suffix + ".restoretmp")
    shutil.copy2(src_db, tmp)
    _fsync_file(tmp)
    os.replace(tmp, dest_db)
    _fsync_dir(dest_db.parent)
    # Drop stale WAL/SHM sidecars from the previous DB so they aren't replayed.
    for sidecar in (f"{dest_db}-wal", f"{dest_db}-shm"):
        try:
            os.remove(sidecar)
        except FileNotFoundError:
            pass


def _swap_dir(src_dir: Path, dest_dir: Path) -> None:
    """Atomically replace dest_dir with a copy of src_dir (move-old-aside, with
    rollback if the final rename fails and reconciliation of a prior crash)."""
    tmp = dest_dir.with_name(dest_dir.name + ".restoretmp")
    old = dest_dir.with_name(dest_dir.name + ".restoreold")

    # Reconcile an interrupted prior swap: live dir gone but moved-aside copy left.
    if old.exists() and not dest_dir.exists():
        os.replace(old, dest_dir)
    if tmp.exists():
        shutil.rmtree(tmp)
    if old.exists():  # safe now: dest_dir is present (or never existed)
        shutil.rmtree(old)

    shutil.copytree(src_dir, tmp)  # build the full copy before touching live dir
    if dest_dir.exists():
        os.replace(dest_dir, old)
    try:
        os.replace(tmp, dest_dir)
    except Exception:
        if old.exists() and not dest_dir.exists():
            os.replace(old, dest_dir)  # roll the live store back
        raise
    if old.exists():
        shutil.rmtree(old)


def _quick_check(db_path: Path) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("PRAGMA quick_check").fetchone()
        return bool(row) and row[0] == "ok"
    finally:
        conn.close()


def _write_sentinel(path: Path, pre_id: str | None, target: str) -> None:
    path.write_text(json.dumps({
        "pre_restore": pre_id,
        "target": target,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }))


def _fsync_file(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:  # pragma: no cover - some filesystems disallow opening dirs
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover - dir fsync unsupported on some platforms
        pass
    finally:
        os.close(fd)
