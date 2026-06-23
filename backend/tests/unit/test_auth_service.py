"""Phase 16.1 (ADR-014) — auth service unit tests."""
from __future__ import annotations

from datetime import timedelta

import pytest

from backend.models.auth import AuthCredential, AuthSession
from backend.services import auth as auth_service


def test_enroll_then_login_resolves_bound_tenant(test_session):
    auth_service.enroll(test_session, "correct horse", tenant_id="default")
    token = auth_service.login(test_session, "correct horse", tenant_id="default")
    assert auth_service.resolve_session(test_session, token) == "default"


def test_secret_never_stored_plaintext(test_session):
    auth_service.enroll(test_session, "super-secret", tenant_id="default")
    cred = test_session.get(AuthCredential, "default")
    assert "super-secret" not in cred.secret_hash
    assert cred.salt  # per-account salt present


def test_token_stored_only_as_digest(test_session):
    auth_service.enroll(test_session, "pw", tenant_id="default")
    token = auth_service.login(test_session, "pw")
    rows = test_session.query(AuthSession).all()
    assert len(rows) == 1
    assert rows[0].token_hash != token  # digest, not the raw token


def test_wrong_secret_rejected(test_session):
    auth_service.enroll(test_session, "right", tenant_id="default")
    with pytest.raises(auth_service.AuthError):
        auth_service.login(test_session, "wrong")


def test_login_before_enroll_rejected(test_session):
    with pytest.raises(auth_service.AuthError):
        auth_service.login(test_session, "anything", tenant_id="default")


def test_double_enroll_rejected(test_session):
    auth_service.enroll(test_session, "pw", tenant_id="default")
    with pytest.raises(auth_service.AuthError):
        auth_service.enroll(test_session, "pw2", tenant_id="default")


def test_empty_secret_rejected(test_session):
    with pytest.raises(auth_service.AuthError):
        auth_service.enroll(test_session, "", tenant_id="default")


def test_no_token_resolves_nothing(test_session):
    # Default-closed: absent/garbage token → no tenant, never a fallback.
    assert auth_service.resolve_session(test_session, None) is None
    assert auth_service.resolve_session(test_session, "garbage") is None


def test_expired_session_resolves_nothing(test_session, monkeypatch):
    auth_service.enroll(test_session, "pw", tenant_id="default")
    monkeypatch.setattr(auth_service, "SESSION_TTL", timedelta(seconds=-1))
    token = auth_service.login(test_session, "pw")
    assert auth_service.resolve_session(test_session, token) is None
    # expired row pruned opportunistically
    assert test_session.query(AuthSession).count() == 0


def test_logout_invalidates_token(test_session):
    auth_service.enroll(test_session, "pw", tenant_id="default")
    token = auth_service.login(test_session, "pw")
    auth_service.logout(test_session, token)
    assert auth_service.resolve_session(test_session, token) is None
