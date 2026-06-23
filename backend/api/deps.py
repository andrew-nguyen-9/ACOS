"""Shared FastAPI dependencies. Leaf module — may import both database and services."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services import auth as auth_service
from backend.services.tenancy import (
    TenantContext,
    ensure_tenant,
    set_session_tenant,
)


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


async def get_tenant_context(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> TenantContext:
    """Resolve the request's tenant from an authenticated session (ADR-014).

    Default-closed: a request with no valid bearer session resolves to **no tenant**
    and is rejected (401) — never a fallback tenant. The tenant is derived
    server-side from the session, so a self-asserted ``X-Tenant-Id`` header can no
    longer select another profile's data (the ADR-008 hole). Declared at the router
    level on tenant-scoped routers, so auth gates each route as part of its contract.
    """
    token = _bearer(authorization)

    tenant_id = await session.run_sync(lambda s: auth_service.resolve_session(s, token))
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="authentication required")

    def _bind(s: Session) -> None:
        ensure_tenant(s, tenant_id)
        set_session_tenant(s, tenant_id)

    await session.run_sync(_bind)
    return TenantContext(tenant_id=tenant_id)
