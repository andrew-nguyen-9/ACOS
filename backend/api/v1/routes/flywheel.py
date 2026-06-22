"""Phase 12.11 read-only flywheel routes.

Surfaces the Skill ROI engine to the UI. Read-side only — no writes here; signals
are emitted from the resume/outcome write paths (12.10 / 12.11).
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.flywheel.skill_roi import rank_skills
from backend.services.flywheel.strategy import recommend
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.tenancy import get_session_tenant

router = APIRouter(tags=["flywheel"])


@router.get("/flywheel/skills/roi")
async def get_skill_roi(
    metric: str = "interview_lift",
    min_n: int = 5,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    def _impl(s: Session) -> dict:
        # tenant resolved at the session boundary / X-Tenant-Id dependency (12.14)
        return rank_skills(s, tenant_id=get_session_tenant(s), metric=metric, min_n=min_n)

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/flywheel/strategy")
async def get_strategy(
    target_jd: str,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Per-tenant resume structure + ATS strategy for a target job description."""
    settings = get_settings()

    def _impl(s: Session) -> dict:
        ollama = OllamaClient(base_url=settings.ollama_base_url)
        extractor = KeywordExtractor(ollama, PromptLoader())
        keywords = extractor.extract(target_jd)
        rec = recommend(s, keywords=keywords, tenant_id=get_session_tenant(s))
        return asdict(rec)

    return await session.run_sync(_impl)
