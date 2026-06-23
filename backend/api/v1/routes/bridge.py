"""Phase 17 (ADR-019) — browser-extension bridge routes.

Two surfaces:
 - `/bridge/pairing-token` is tenant-scoped (authed via the normal session): the app
   mints the one-time pairing token to show the user.
 - `/bridge/ping` + `/bridge/capture` are gated by the X-Bridge-Token header (the
   paired extension), NOT a bearer session. Default-closed: no/invalid token → 401.

Capture (17.4) creates an Application *draft* the user reviews — never submits
anything (ADR-012). Captured text passes the ADR-017 injection screen (16.4).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.api.deps import get_tenant_context
from backend.database import get_async_session
from backend.repositories.application import ApplicationRepository
from backend.security import injection
from backend.security.injection import InjectionBlocked
from backend.services import bridge
from backend.services.tenancy import ensure_tenant, set_session_tenant

# Tenant-scoped (authed) — mounted with the tenant dependency in main.py.
pairing_router = APIRouter(tags=["bridge"], dependencies=[Depends(get_tenant_context)])
# Token-gated (extension) — its own auth via X-Bridge-Token, no bearer session.
bridge_router = APIRouter(tags=["bridge"])


@pairing_router.post("/bridge/pairing-token")
async def create_pairing_token(session: AsyncSession = Depends(get_async_session)) -> dict:
    from backend.services.tenancy import get_session_tenant

    def _impl(s: Session) -> str:
        tenant_id = get_session_tenant(s) or "default"
        return bridge.generate_pairing(s, tenant_id)

    token = await session.run_sync(_impl)
    return {"pairing_token": token}


def _resolve_bridge_tenant(session: Session, token: str | None) -> str:
    tenant_id = bridge.resolve_pairing(session, token)
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="extension not paired")
    ensure_tenant(session, tenant_id)
    set_session_tenant(session, tenant_id)
    return tenant_id


@bridge_router.get("/bridge/ping")
async def bridge_ping(
    x_bridge_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    await session.run_sync(lambda s: _resolve_bridge_tenant(s, x_bridge_token))
    return {"ok": True, "app": "acos"}


class CaptureRequest(BaseModel):
    title: str = Field(min_length=1)
    company: str = ""
    job_url: str | None = None
    responsibilities: str = ""
    qualifications: str = ""
    raw_text: str = ""


@bridge_router.post("/bridge/capture")
async def bridge_capture(
    body: CaptureRequest,
    x_bridge_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """One-click capture → reviewable Application draft (ADR-012: never submits)."""

    def _impl(s: Session) -> dict:
        _resolve_bridge_tenant(s, x_bridge_token)
        # ADR-017 injection screen on the captured (untrusted) text before storing.
        jd = "\n\n".join(
            p for p in [body.responsibilities, body.qualifications, body.raw_text] if p
        )
        try:
            jd = injection.screen(s, jd, source="extension")
        except InjectionBlocked as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        repo = ApplicationRepository(s)
        # De-dupe: same company+position already a draft → return it, don't double-create.
        if body.job_url:
            for existing in repo.get_by_status("draft"):
                if existing.job_url and existing.job_url == body.job_url:
                    return {"id": existing.id, "status": existing.status, "deduped": True}

        app = repo.create(
            company=body.company or "(unknown)",
            position=body.title,
            job_description=jd or None,
            job_url=body.job_url,
            status="draft",  # ADR-012: review-not-submit
            source="other",
        )
        return {"id": app.id, "status": app.status, "deduped": False}

    return await session.run_sync(_impl)
