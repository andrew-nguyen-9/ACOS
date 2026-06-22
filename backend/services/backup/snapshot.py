"""Backup snapshots (Phase 11.4) — local-first, restorable system archives.

A snapshot is a timestamped directory under ``database/backups/`` containing:
  - ``acos.db``           consistent SQLite copy via the online backup API
                          (WAL-safe; works while the DB is open — verified via context7)
  - ``chroma/``           directory copy of the Chroma persistent store
  - ``prompt_registry.json`` / ``system_config.json``  human-readable dumps
  - ``manifest.json``     metadata only (versions, hashes, counts) — NO secrets

Incremental snapshots always copy the DB (cheap, full copy is fine at this
scale) but skip the Chroma directory when its content hash matches the most
recent snapshot. Everything is written owner-only (0700 dir / 0600 files)
because backups hold personal career data (CLAUDE.md security reqs, ADR-001
local-only).

# ponytail: full-directory hash for the incremental skip; upgrade to per-file
# diffing only if Chroma stores grow enough that re-copying hurts.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.models.optimization import PromptVersion
from backend.models.system_config import SystemConfig

logger = logging.getLogger(__name__)

_DIR_MODE = 0o700
_FILE_MODE = 0o600
_DB_NAME = "acos.db"


@dataclass
class SnapshotMeta:
    id: str
    path: str
    full: bool
    created_at: str
    chroma_included: bool
    chroma_hash: str | None
    app_version: str


def _now_id(full: bool) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{ts}__{'full' if full else 'incr'}"


def _hash_dir(path: Path) -> str | None:
    """Stable content hash of a directory tree, or None if it doesn't exist.

    A file read error (deleted mid-walk, transient I/O) folds into the hash as a
    marker rather than aborting: this hash runs before *every* maintenance action
    (executor snapshots first), so a Chroma read hiccup must not block maintenance —
    it just makes the store look 'changed' and triggers a copy.
    """
    if not path.is_dir():
        return None
    h = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(file.relative_to(path)).encode())
        try:
            h.update(file.read_bytes())
        except OSError as exc:
            h.update(f"__unreadable__{exc}".encode())
    return h.hexdigest()


def _secure(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:  # pragma: no cover - filesystem may not support chmod
        pass


def _backup_sqlite(src_path: str, dest_path: Path) -> None:
    """Copy the live SQLite DB via the online backup API (consistent, WAL-safe)."""
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dest_path)
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


def _previous_chroma_hash(backups_dir: Path) -> str | None:
    for meta in list_snapshots(backups_dir):
        if meta.chroma_hash is not None:
            return meta.chroma_hash
    return None


def snapshot(
    session: Session,
    *,
    full: bool = True,
    backups_dir: str | Path = "database/backups",
    db_path: str = "database/acos.db",
    chroma_path: str = "database/chroma",
    app_version: str = "0.0.0",
) -> SnapshotMeta:
    backups_dir = Path(backups_dir)
    chroma_src = Path(chroma_path)
    snap_id = _now_id(full)
    dest = backups_dir / snap_id
    dest.mkdir(parents=True, exist_ok=False)
    _secure(dest, _DIR_MODE)

    # On any failure, remove the partial snapshot dir so it can't be mistaken for
    # a real backup (the manifest is written last, so list_snapshots ignores it,
    # but a truncated acos.db on disk is misleading and accumulates).
    try:
        # 1. SQLite — always copied.
        db_dest = dest / _DB_NAME
        _backup_sqlite(db_path, db_dest)
        _secure(db_dest, _FILE_MODE)

        # 2. Chroma — copied for full; for incremental, only if its hash changed.
        chroma_hash = _hash_dir(chroma_src)
        chroma_included = False
        if chroma_hash is not None:
            unchanged = (not full) and chroma_hash == _previous_chroma_hash(backups_dir)
            if not unchanged:
                shutil.copytree(chroma_src, dest / "chroma")
                chroma_included = True

        # 3. Auxiliary JSON dumps (inspection/portability; DB is the restore source).
        _dump_json(dest / "prompt_registry.json", _dump_prompts(session))
        _dump_json(dest / "system_config.json", _dump_config(session))

        created_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        manifest = {
            "id": snap_id,
            "created_at": created_at,
            "full": full,
            "app_version": app_version,
            "db_file": _DB_NAME,
            "chroma_included": chroma_included,
            "chroma_hash": chroma_hash,
        }
        _dump_json(dest / "manifest.json", manifest)
    except Exception as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError(f"snapshot failed (db={db_path}, dest={dest}): {exc}") from exc

    return SnapshotMeta(
        id=snap_id, path=str(dest), full=full, created_at=created_at,
        chroma_included=chroma_included, chroma_hash=chroma_hash, app_version=app_version,
    )


def list_snapshots(backups_dir: str | Path = "database/backups") -> list[SnapshotMeta]:
    """All snapshots with a readable manifest, newest first."""
    backups_dir = Path(backups_dir)
    if not backups_dir.is_dir():
        return []
    out: list[SnapshotMeta] = []
    for child in backups_dir.iterdir():
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            m = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out.append(SnapshotMeta(
            id=m["id"], path=str(child), full=m["full"], created_at=m["created_at"],
            chroma_included=m["chroma_included"], chroma_hash=m.get("chroma_hash"),
            app_version=m.get("app_version", "?"),
        ))
    return sorted(out, key=lambda s: s.created_at, reverse=True)


def _dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2))
    _secure(path, _FILE_MODE)


def _dump_prompts(session: Session) -> list[dict]:
    # Best-effort: the JSON dumps are auxiliary (the DB copy is the restore source),
    # so a missing/partial table must not abort the snapshot.
    try:
        return [
            {
                "prompt_name": v.prompt_name, "version": v.version, "is_active": v.is_active,
                "parent_version": v.parent_version, "content_yaml": v.content_yaml,
                "created_at": v.created_at,
            }
            for v in session.query(PromptVersion).all()
        ]
    except Exception:
        logger.warning("prompt_registry dump failed; writing empty dump", exc_info=True)
        session.rollback()
        return []


def _dump_config(session: Session) -> dict:
    try:
        return {c.key: c.value for c in session.query(SystemConfig).all()}
    except Exception:
        logger.warning("system_config dump failed; writing empty dump", exc_info=True)
        session.rollback()
        return {}
