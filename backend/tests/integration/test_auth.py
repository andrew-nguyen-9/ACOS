"""Phase 16.1 (ADR-014) — auth route + default-closed integration tests.

Uses `unauth_client` (the real tenant-context dependency, no override) so the auth
gate is exercised end to end. `/api/v1/applications` is a representative
tenant-scoped route.
"""
from __future__ import annotations

SCOPED = "/api/v1/applications"


def _enroll_and_login(client, secret="correct horse battery"):
    r = client.post("/api/v1/auth/enroll", json={"secret": secret})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_scoped_route_without_session_is_401(unauth_client):
    # Default-closed: no bearer → no tenant → rejected, never a fallback tenant.
    r = unauth_client.get(SCOPED)
    assert r.status_code == 401


def test_self_asserted_tenant_header_is_rejected(unauth_client):
    # The ADR-008 hole: naming a tenant without a session must NOT grant access.
    r = unauth_client.get(SCOPED, headers={"X-Tenant-Id": "default"})
    assert r.status_code == 401


def test_valid_session_grants_access(unauth_client):
    token = _enroll_and_login(unauth_client)
    r = unauth_client.get(SCOPED, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_garbage_token_is_401(unauth_client):
    _enroll_and_login(unauth_client)
    r = unauth_client.get(SCOPED, headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_enroll_status_and_double_enroll(unauth_client):
    assert unauth_client.get("/api/v1/auth/status").json() == {"enrolled": False}
    _enroll_and_login(unauth_client)
    assert unauth_client.get("/api/v1/auth/status").json() == {"enrolled": True}
    # second enroll is rejected (no silent credential reset)
    r = unauth_client.post("/api/v1/auth/enroll", json={"secret": "other"})
    assert r.status_code == 409


def test_login_wrong_secret_is_401(unauth_client):
    _enroll_and_login(unauth_client, secret="the-right-one")
    r = unauth_client.post("/api/v1/auth/login", json={"secret": "the-wrong-one"})
    assert r.status_code == 401


def test_logout_invalidates_session(unauth_client):
    token = _enroll_and_login(unauth_client)
    h = {"Authorization": f"Bearer {token}"}
    assert unauth_client.get(SCOPED, headers=h).status_code == 200
    assert unauth_client.post("/api/v1/auth/logout", headers=h).status_code == 200
    assert unauth_client.get(SCOPED, headers=h).status_code == 401
