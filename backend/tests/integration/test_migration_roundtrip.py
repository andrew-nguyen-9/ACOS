"""Every Alembic migration must round-trip upgrade→downgrade→upgrade (Phase 11.1).

Runs the full revision chain on a throwaway temp SQLite DB. This surfaces any
migration whose ``downgrade()`` is missing or broken (see database/README.md).
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _alembic_config() -> Config:
    cfg = Config(str(_REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_REPO_ROOT / "database" / "migrations"))
    return cfg


def test_migrations_roundtrip(tmp_path, monkeypatch):
    # Point settings (which env.py reads for sqlalchemy.url) at a temp DB.
    monkeypatch.setenv("ACOS_DB_PATH", str(tmp_path / "roundtrip.db"))
    get_settings.cache_clear()
    try:
        cfg = _alembic_config()
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
    finally:
        get_settings.cache_clear()  # restore real settings for other tests
