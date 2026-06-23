"""Phase 12.1 — verify the SQLite hot-path pragmas are applied per connection.

A file-backed DB is required: ``:memory:`` cannot run WAL (no ``-wal`` sidecar),
so these tests open a real temp DB via ``build_engine`` rather than the in-memory
conftest engine.
"""
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine

_WAL = "wal"
_SYNCHRONOUS_NORMAL = 1
_MMAP_256MB = 268_435_456
_FK_ON = 1


def _read_pragmas(session: Session) -> tuple[str, int, int, int]:
    jm = session.execute(text("PRAGMA journal_mode")).scalar_one()
    sync = session.execute(text("PRAGMA synchronous")).scalar_one()
    mmap = session.execute(text("PRAGMA mmap_size")).scalar_one()
    fk = session.execute(text("PRAGMA foreign_keys")).scalar_one()
    return str(jm), int(sync), int(mmap), int(fk)


def _engine_for(tmp_path: Path):
    return build_engine(f"sqlite:///{tmp_path / 'pragma.db'}")


def test_pragmas_applied_on_connection(tmp_path: Path) -> None:
    engine = _engine_for(tmp_path)
    make_session = sessionmaker(bind=engine)
    try:
        with make_session() as session:
            jm, sync, mmap, fk = _read_pragmas(session)
        assert jm == _WAL
        assert sync == _SYNCHRONOUS_NORMAL
        assert mmap == _MMAP_256MB
        assert fk == _FK_ON
    finally:
        engine.dispose()


def test_pragmas_reapplied_on_second_connection(tmp_path: Path) -> None:
    """synchronous/mmap/foreign_keys are per-connection; dispose forces a fresh
    dbapi connection so the connect hook must re-apply them."""
    engine = _engine_for(tmp_path)
    make_session = sessionmaker(bind=engine)
    try:
        with make_session() as first:
            _read_pragmas(first)
        engine.dispose()  # drop the pooled connection -> next session reconnects
        with make_session() as second:
            jm, sync, mmap, fk = _read_pragmas(second)
        assert jm == _WAL  # persistent in the file header
        assert sync == _SYNCHRONOUS_NORMAL
        assert mmap == _MMAP_256MB
        assert fk == _FK_ON
    finally:
        engine.dispose()
