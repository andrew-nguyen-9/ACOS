"""Phase 16.1 auth tables (ADR-014) — the credential verifier + short-lived sessions
that bind a request to a tenant.

These are NOT ``TenantScopedMixin`` rows: they *establish* the tenant binding, so
they must be reachable before any tenant is in scope (login happens before the
tenant is known). The long-lived account secret never lives here — only a one-way
scrypt verifier of it (the secret itself sits in the OS Keychain, ADR-014 §2). A
session stores only a SHA-256 digest of its bearer token, never the token.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utcnow


class AuthCredential(Base):
    """One enrolled account per tenant: a scrypt verifier of its account secret."""

    __tablename__ = "auth_credentials"

    tenant_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tenants.id"), primary_key=True
    )
    # scrypt(secret, salt) — base64; salt stored alongside. Never the secret.
    secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)


class AuthSession(Base):
    """A short-lived bearer session. Only the token digest is stored (ADR-014 §2:
    the sidecar holds a short-lived token, not the long-lived secret)."""

    __tablename__ = "auth_sessions"

    # SHA-256 hex of the bearer token — lookups hash the presented token and match.
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tenants.id"), nullable=False, index=True
    )
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
