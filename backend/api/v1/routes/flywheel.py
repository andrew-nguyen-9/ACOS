"""Phase 12.11 read-only flywheel routes.

Surfaces the Skill ROI engine to the UI. Read-side only — no writes here; signals
are emitted from the resume/outcome write paths (12.10 / 12.11).
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.flywheel.global_patterns import global_skill_roi
from backend.services.flywheel.prompt_evolution import PromptEvolutionService
from backend.services.flywheel.skill_roi import rank_skills
from backend.services.flywheel.strategy import recommend
from backend.services.ollama_client import OllamaClient
from backend.services.optimization.guardrails import GuardrailViolation
from backend.services.prompt_loader import PromptLoader
from backend.services.tenancy import get_session_tenant

router = APIRouter(tags=["flywheel"])


class ProposeRequest(BaseModel):
    prompt_name: str
    proposed_content: str
    signal_ids: list[str]
    rationale: str
    expected_impact: str
    confidence_level: str = "strong_inference"
    risk_level: str = "low"


class TrialRequest(BaseModel):
    prompt_name: str
    version: str


class PromoteRequest(BaseModel):
    prompt_name: str
    version: str
    approved_by: str


class RollbackRequest(BaseModel):
    prompt_name: str
    approved_by: str = "user"


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


class StrategyRequest(BaseModel):
    target_jd: str


@router.post("/flywheel/strategy")
async def get_strategy(
    req: StrategyRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Per-tenant resume structure + ATS strategy for a target job description.

    POST, not GET: a pasted JD can be many KB, which would blow the URL/header
    limit as a query param (414). It travels in the request body instead.
    """
    settings = get_settings()

    def _impl(s: Session) -> dict:
        ollama = OllamaClient(base_url=settings.ollama_base_url)
        extractor = KeywordExtractor(ollama, PromptLoader())
        keywords = extractor.extract(req.target_jd)
        rec = recommend(s, keywords=keywords, tenant_id=get_session_tenant(s))
        return asdict(rec)

    return await session.run_sync(_impl)


@router.get("/flywheel/global/roi")
async def get_global_roi(
    metric: str = "interview_lift",
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Cross-tenant skill ROI rankings — aggregate-only, k-anonymized (ADR-009).

    No per-tenant attribution: each row carries a contributing-tenant COUNT, not ids.
    """
    rankings = await session.run_sync(
        lambda s: global_skill_roi(s, metric=metric)
    )
    return {"metric": metric, "rankings": rankings}


def _version_dict(v) -> dict:
    return {"id": v.id, "prompt_name": v.prompt_name, "version": v.version,
            "is_active": v.is_active, "parent_version": v.parent_version,
            "change_rationale": v.change_rationale}


@router.post("/flywheel/prompt/propose")
async def propose_prompt(body: ProposeRequest, session: AsyncSession = Depends(get_async_session)) -> dict:
    """Create a candidate prompt version (inactive) with a signal-linked rationale."""
    def _impl(s: Session) -> dict:
        cand = PromptEvolutionService(s).propose(
            body.prompt_name, body.proposed_content, signal_ids=body.signal_ids,
            rationale=body.rationale, expected_impact=body.expected_impact,
            confidence_level=body.confidence_level, risk_level=body.risk_level,
        )
        return _version_dict(cand)

    try:
        return await session.run_sync(_impl)
    except (ValueError, GuardrailViolation) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/flywheel/prompt/trial")
async def trial_prompt(body: TrialRequest, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        exp = PromptEvolutionService(s).trial(body.prompt_name, body.version)
        return {"experiment_id": exp.id, "name": exp.name, "status": exp.status}

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/flywheel/prompt/promote")
async def promote_prompt(body: PromoteRequest, session: AsyncSession = Depends(get_async_session)) -> dict:
    """Flip the active prompt pointer — requires explicit approval (audited)."""
    def _impl(s: Session) -> dict:
        return _version_dict(
            PromptEvolutionService(s).promote(body.prompt_name, body.version, approved_by=body.approved_by)
        )

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/flywheel/prompt/rollback")
async def rollback_prompt(body: RollbackRequest, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        return _version_dict(
            PromptEvolutionService(s).rollback(body.prompt_name, approved_by=body.approved_by)
        )

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
