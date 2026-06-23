"""Phase 12.14 tenancy service — the request-scoped TenantContext + guard helpers.

The active tenant lives on ``session.info["tenant_id"]`` (set once at the session
boundary, ADR-008). Repositories call ``require_session_tenant`` to turn a missing
tenant into a hard error rather than a silent full-table read.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.tenant import TENANT_INFO_KEY, Tenant, TenantScopedMixin

DEFAULT_TENANT_ID = "default"


class TenantScopeError(RuntimeError):
    """A tenant-scoped query ran with no tenant in scope — a leak was prevented."""


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str


def is_tenant_scoped(model: type) -> bool:
    return isinstance(model, type) and issubclass(model, TenantScopedMixin)


def set_session_tenant(session: Session, tenant_id: str) -> None:
    session.info[TENANT_INFO_KEY] = tenant_id


def get_session_tenant(session: Session) -> str | None:
    return session.info.get(TENANT_INFO_KEY)


def require_session_tenant(session: Session) -> str:
    tenant_id = session.info.get(TENANT_INFO_KEY)
    if not tenant_id:
        raise TenantScopeError(
            "tenant-scoped query with no tenant in scope; "
            "resolve a TenantContext / call set_session_tenant() first"
        )
    return tenant_id


def ensure_tenant(session: Session, tenant_id: str, name: str | None = None) -> Tenant:
    """Idempotent get-or-create of a tenant row (FK target for scoped inserts)."""
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=name or tenant_id)
        session.add(tenant)
        session.flush()
    return tenant


def ensure_default_tenant(session: Session) -> str:
    ensure_tenant(session, DEFAULT_TENANT_ID, "default")
    return DEFAULT_TENANT_ID
