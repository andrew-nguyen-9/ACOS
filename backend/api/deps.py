"""Shared FastAPI dependencies. Leaf module — may import both database and services."""
from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services.tenancy import (
    DEFAULT_TENANT_ID,
    TenantContext,
    ensure_tenant,
    set_session_tenant,
)


async def get_tenant_context(
    x_tenant_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> TenantContext:
    """Resolve the request's tenant and bind it to the session.

    Single-user resolves to ``default``; an optional ``X-Tenant-Id`` header selects a
    local profile (forward-compat for a multi-profile UI). Declared at the router level
    on tenant-scoped routers, so the active tenant is part of each route's contract as
    well as enforced at the session layer (ADR-008 belt-and-suspenders).
    """
    tenant_id = x_tenant_id or DEFAULT_TENANT_ID

    def _bind(s: Session) -> None:
        ensure_tenant(s, tenant_id)
        set_session_tenant(s, tenant_id)

    await session.run_sync(_bind)
    return TenantContext(tenant_id=tenant_id)
