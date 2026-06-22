"""Phase 11.4 — full + incremental snapshots (SQLite online backup + Chroma copy)."""
from __future__ import annotations

import json
import sqlite3
import stat
from pathlib import Path

from backend.services.backup.snapshot import snapshot, list_snapshots


def _make_db(path: Path, value: str = "hello") -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.execute("INSERT INTO t VALUES (?)", (value,))
    conn.commit()
    conn.close()


def _make_chroma(path: Path, contents: str = "vectors") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "chroma.sqlite3").write_text(contents)


def test_full_snapshot_creates_manifest_and_restorable_db(tmp_path, test_session):
    db = tmp_path / "acos.db"
    chroma = tmp_path / "chroma"
    backups = tmp_path / "backups"
    _make_db(db)
    _make_chroma(chroma)

    meta = snapshot(
        test_session, full=True, backups_dir=backups,
        db_path=str(db), chroma_path=str(chroma), app_version="0.1.0",
    )

    dest = Path(meta.path)
    assert dest.is_dir()
    manifest = json.loads((dest / "manifest.json").read_text())
    assert manifest["full"] is True
    assert manifest["app_version"] == "0.1.0"
    assert manifest["chroma_included"] is True

    # DB copy is a real, queryable SQLite file with the original row.
    copied = sqlite3.connect(dest / "acos.db")
    assert copied.execute("SELECT v FROM t").fetchone()[0] == "hello"
    copied.close()

    assert (dest / "chroma" / "chroma.sqlite3").exists()
    assert (dest / "prompt_registry.json").exists()
    assert (dest / "system_config.json").exists()


def test_incremental_skips_unchanged_chroma_but_always_copies_db(tmp_path, test_session):
    db = tmp_path / "acos.db"
    chroma = tmp_path / "chroma"
    backups = tmp_path / "backups"
    _make_db(db)
    _make_chroma(chroma)

    snapshot(test_session, full=True, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    meta = snapshot(test_session, full=False, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))

    dest = Path(meta.path)
    assert meta.chroma_included is False
    assert not (dest / "chroma").exists()      # unchanged → skipped
    assert (dest / "acos.db").exists()          # DB always copied


def test_incremental_includes_changed_chroma(tmp_path, test_session):
    db = tmp_path / "acos.db"
    chroma = tmp_path / "chroma"
    backups = tmp_path / "backups"
    _make_db(db)
    _make_chroma(chroma)

    snapshot(test_session, full=True, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))
    (chroma / "chroma.sqlite3").write_text("CHANGED vectors")  # mutate store
    meta = snapshot(test_session, full=False, backups_dir=backups, db_path=str(db), chroma_path=str(chroma))

    assert meta.chroma_included is True
    assert (Path(meta.path) / "chroma" / "chroma.sqlite3").exists()


def test_snapshot_without_chroma_dir_is_db_only(tmp_path, test_session):
    db = tmp_path / "acos.db"
    _make_db(db)
    meta = snapshot(
        test_session, full=True, backups_dir=tmp_path / "backups",
        db_path=str(db), chroma_path=str(tmp_path / "missing_chroma"),
    )
    assert meta.chroma_included is False
    assert meta.chroma_hash is None


def test_snapshot_files_are_local_only_perms(tmp_path, test_session):
    db = tmp_path / "acos.db"
    _make_db(db)
    meta = snapshot(test_session, full=True, backups_dir=tmp_path / "backups", db_path=str(db),
                    chroma_path=str(tmp_path / "nochroma"))
    dest = Path(meta.path)
    # Directory: owner-only (0o700). Files: owner rw (0o600). No group/other bits.
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    assert stat.S_IMODE((dest / "manifest.json").stat().st_mode) == 0o600


def test_manifest_contains_no_config_values(tmp_path, test_session):
    # Manifest is metadata only — never embeds secrets/config values.
    from backend.repositories.system_config import SystemConfigRepository

    SystemConfigRepository(test_session).set_value("github_token", "supersecret")
    db = tmp_path / "acos.db"
    _make_db(db)
    meta = snapshot(test_session, full=True, backups_dir=tmp_path / "backups", db_path=str(db),
                    chroma_path=str(tmp_path / "nochroma"))
    manifest_text = (Path(meta.path) / "manifest.json").read_text()
    assert "supersecret" not in manifest_text


def test_list_snapshots_returns_newest_first(tmp_path, test_session):
    db = tmp_path / "acos.db"
    _make_db(db)
    backups = tmp_path / "backups"
    m1 = snapshot(test_session, full=True, backups_dir=backups, db_path=str(db),
                  chroma_path=str(tmp_path / "nochroma"))
    m2 = snapshot(test_session, full=False, backups_dir=backups, db_path=str(db),
                  chroma_path=str(tmp_path / "nochroma"))
    listed = list_snapshots(backups)
    ids = [s.id for s in listed]
    assert ids == [m2.id, m1.id]
