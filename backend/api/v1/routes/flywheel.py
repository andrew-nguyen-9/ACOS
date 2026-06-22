"""Phase 12.11 read-only flywheel routes.

Surfaces the Skill ROI engine to the UI. Read-side only — no writes here; signals
are emitted from the resume/outcome write paths (12.10 / 12.11).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services.flywheel.skill_roi import rank_skills

router = APIRouter(tags=["flywheel"])


@router.get("/flywheel/skills/roi")
async def get_skill_roi(
    metric: str = "interview_lift",
    min_n: int = 5,
    tenant_id: str | None = None,  # 12.14 forward-compat; None = single-tenant today
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    def _impl(s: Session) -> dict:
        return rank_skills(s, tenant_id=tenant_id, metric=metric, min_n=min_n)

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
