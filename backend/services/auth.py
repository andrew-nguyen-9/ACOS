"""Phase 16.1 auth service (ADR-014) — enroll, login, session resolution.

Trust model: the long-lived account *secret* lives in the OS Keychain (Rust side).
The backend never stores it — only a scrypt verifier. On login the backend mints a
random bearer token, stores its SHA-256 digest with an expiry, and hands the raw
token back; every later request presents that token. No token in scope → no tenant
(default-closed, the ADR-008 hole this closes).

No new dependency: stdlib ``hashlib.scrypt`` is the KDF and ``secrets`` the RNG.
(Argon2 arrives in 16.2 for at-rest encryption; auth doesn't need it.)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.models.auth import AuthCredential, AuthSession
from backend.services.tenancy import DEFAULT_TENANT_ID, ensure_tenant

# scrypt work factors — interactive-login cost, fixed (changing them invalidates
# existing verifiers; a re-enroll re-hashes at the new cost).
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32

SESSION_TTL = timedelta(hours=12)


class AuthError(RuntimeError):
    """Enrollment/login precondition failure (already enrolled, bad secret)."""


def _hash_secret(secret: str, salt: bytes) -> str:
    dk = hashlib.scrypt(
        secret.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN
    )
    return base64.b64encode(dk).decode("ascii")


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_enrolled(session: Session, tenant_id: str = DEFAULT_TENANT_ID) -> bool:
    return session.get(AuthCredential, tenant_id) is not None


def enroll(session: Session, secret: str, tenant_id: str = DEFAULT_TENANT_ID,
           name: str | None = None) -> None:
    """Register the account secret for a tenant. One-time; re-enroll is rejected so a
    stray request can't silently reset credentials."""
    if not secret:
        raise AuthError("empty secret")
    if is_enrolled(session, tenant_id):
        raise AuthError("already enrolled")
    ensure_tenant(session, tenant_id, name)
    salt = secrets.token_bytes(16)
    session.add(
        AuthCredential(
            tenant_id=tenant_id,
            secret_hash=_hash_secret(secret, salt),
            salt=base64.b64encode(salt).decode("ascii"),
        )
    )
    session.flush()


def login(session: Session, secret: str, tenant_id: str = DEFAULT_TENANT_ID) -> str:
    """Verify the secret and mint a bearer token. Returns the raw token (stored only
    as a digest). Constant-time compare so a wrong secret leaks no timing signal."""
    cred = session.get(AuthCredential, tenant_id)
    if cred is None:
        raise AuthError("not enrolled")
    salt = base64.b64decode(cred.salt)
    if not hmac.compare_digest(_hash_secret(secret, salt), cred.secret_hash):
        raise AuthError("invalid secret")
    token = secrets.token_urlsafe(32)
    session.add(
        AuthSession(
            token_hash=_token_digest(token),
            tenant_id=tenant_id,
            expires_at=(_now() + SESSION_TTL).isoformat(timespec="microseconds"),
        )
    )
    session.flush()
    return token


def resolve_session(session: Session, token: str | None) -> str | None:
    """Return the bound tenant for a valid, unexpired token, else None (default-closed).
    An expired row is deleted opportunistically."""
    if not token:
        return None
    row = session.get(AuthSession, _token_digest(token))
    if row is None:
        return None
    if datetime.fromisoformat(row.expires_at) <= _now():
        session.delete(row)
        session.flush()
        return None
    return row.tenant_id


def logout(session: Session, token: str | None) -> None:
    if not token:
        return
    row = session.get(AuthSession, _token_digest(token))
    if row is not None:
        session.delete(row)
        session.flush()
