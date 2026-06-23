"""Phase 14.3 — Application.notes encrypted at rest end-to-end when opted in."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.config import get_settings
from backend.models.application import Application
from backend.services.tenancy import require_session_tenant


@pytest.fixture
def fernet_key():
    fernet = pytest.importorskip("cryptography.fernet")
    return fernet.Fernet.generate_key().decode()


def _make_app(session, notes: str) -> str:
    tid = require_session_tenant(session)
    app = Application(company="Acme", position="PM", notes=notes, tenant_id=tid)
    session.add(app)
    session.commit()
    return app.id


def test_notes_ciphertext_at_rest_plaintext_via_orm(monkeypatch, test_session, fernet_key):
    monkeypatch.setenv("ACOS_ENABLE_ENCRYPTED_STORAGE", "1")
    monkeypatch.setenv("ACOS_ENCRYPTION_KEY", fernet_key)
    get_settings.cache_clear()
    try:
        secret = "comp target 200k, do not share"
        app_id = _make_app(test_session, secret)

        # Raw cell is ciphertext — a stolen DB file does not reveal the note.
        raw = test_session.execute(
            text("SELECT notes FROM applications WHERE id = :id"), {"id": app_id}
        ).scalar_one()
        assert raw != secret
        assert "200k" not in raw

        # ORM read transparently decrypts.
        test_session.expire_all()
        got = test_session.get(Application, app_id)
        assert got is not None and got.notes == secret
    finally:
        get_settings.cache_clear()


def test_off_path_stores_plaintext(monkeypatch, test_session):
    monkeypatch.delenv("ACOS_ENABLE_ENCRYPTED_STORAGE", raising=False)
    get_settings.cache_clear()
    try:
        app_id = _make_app(test_session, "ordinary note")
        raw = test_session.execute(
            text("SELECT notes FROM applications WHERE id = :id"), {"id": app_id}
        ).scalar_one()
        # OFF path is unchanged — stored exactly as written (byte-identical Text).
        assert raw == "ordinary note"
    finally:
        get_settings.cache_clear()
