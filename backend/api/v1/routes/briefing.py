"""15.4 — Daily Career Briefing read surface.

GET /briefing composes the five briefing sections off the hot path (a read
rollup over the existing engines). Recommend-only (ADR-012): no outbound action.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services.briefing.service import BriefingService

router = APIRouter(tags=["briefing"])


@router.get("/briefing")
async def get_briefing(session: AsyncSession = Depends(get_async_session)) -> dict:
    return await session.run_sync(lambda s: BriefingService(s).compose())
