from __future__ import annotations

from typing import NoReturn
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.repositories.optimization import (
    OptimizationProposalRepository, OptimizationLogRepository,
)
from backend.services.optimization.applier import Applier, ApprovalRequired
from backend.services.optimization.recommender import Recommender
from backend.services.optimization.loop import LearningLoop
from backend.services import audit
from backend.security import permissions

router = APIRouter(tags=["optimization"])


def _serialize_proposal(p) -> dict:
    return {
        "id": p.id, "target_engine": p.target_engine,
        "target_parameter": p.target_parameter, "current_value": p.current_value,
        "proposed_value": p.proposed_value, "rationale": p.rationale,
        "expected_impact": p.expected_impact, "confidence_level": p.confidence_level,
        "risk_level": p.risk_level, "evidence_json": p.evidence_json,
        "status": p.status, "created_at": p.created_at,
        "updated_at": p.updated_at, "decided_at": p.decided_at,
    }


def _serialize_log(l) -> dict:
    return {
        "id": l.id, "proposal_id": l.proposal_id, "action": l.action,
        "target_engine": l.target_engine, "target_parameter": l.target_parameter,
        "old_value": l.old_value, "new_value": l.new_value,
        "actor": l.actor, "created_at": l.created_at,
    }


@router.get("/optimization/proposals")
async def list_proposals(
    status: str | None = Query(default=None), session: AsyncSession = Depends(get_async_session)
) -> dict:
    def _impl(s: Session) -> dict:
        repo = OptimizationProposalRepository(s)
        rows = repo.list_by_status(status) if status else repo.list()
        return {"proposals": [_serialize_proposal(p) for p in rows]}

    return await session.run_sync(_impl)


@router.post("/optimization/proposals/generate")
async def generate_proposals(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        # 16.6 (ADR-018): enforce the module's capability manifest (default-closed).
        permissions.require("optimization", action="optimization", resource="optimization_proposals", session=s)
        created = Recommender(s).generate_proposals()
        # 16.3 (ADR-016): audit the optimization recommendation — counts, no bodies.
        audit.safe_record(s, "optimization", {"created": len(created)})
        return {"created": len(created), "proposal_ids": [p.id for p in created]}

    return await session.run_sync(_impl)


@router.post("/optimization/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_proposal(Applier(s).approve(proposal_id))
        )
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)


@router.post("/optimization/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_proposal(Applier(s).reject(proposal_id))
        )
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)


@router.post("/optimization/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_log(Applier(s).apply(proposal_id))
        )
    except ApprovalRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/optimization/proposals/{proposal_id}/revert")
async def revert_proposal(proposal_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_log(Applier(s).revert(proposal_id))
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/optimization/logs")
async def list_logs(limit: int = 50, session: AsyncSession = Depends(get_async_session)) -> dict:
    logs = await session.run_sync(lambda s: OptimizationLogRepository(s).list_recent(limit=limit))
    return {"logs": [_serialize_log(l) for l in logs]}


@router.post("/optimization/loop/run")
async def run_loop(session: AsyncSession = Depends(get_async_session)) -> dict:
    return await session.run_sync(lambda s: LearningLoop(s).maybe_run())


def _raise_not_found_or_conflict(exc: ValueError) -> NoReturn:
    msg = str(exc)
    if "not found" in msg:
        raise HTTPException(status_code=404, detail=msg)
    raise HTTPException(status_code=409, detail=msg)


from pydantic import BaseModel
from backend.repositories.optimization import (
    ABExperimentRepository, ABVariantRepository, PromptVersionRepository,
)
from backend.services.optimization.ab_testing import ABTestingService
from backend.services.optimization.prompt_evolver import PromptEvolver


class CreateExperimentRequest(BaseModel):
    name: str
    target_engine: str
    variant_a: dict
    variant_b: dict


def _serialize_experiment(exp, variants, svc) -> dict:
    return {
        "id": exp.id, "name": exp.name, "target_engine": exp.target_engine,
        "metric": exp.metric, "status": exp.status,
        "winner_variant_id": exp.winner_variant_id,
        "created_at": exp.created_at, "concluded_at": exp.concluded_at,
        "variants": [
            {
                "id": v.id, "label": v.label,
                "impressions": v.impressions, "conversions": v.conversions,
                "conversion_rate": svc.conversion_rate(v.id),
            }
            for v in variants
        ],
    }


def _serialize_version(v) -> dict:
    return {
        "id": v.id, "prompt_name": v.prompt_name, "version": v.version,
        "is_active": v.is_active, "parent_version": v.parent_version,
        "change_rationale": v.change_rationale, "created_at": v.created_at,
    }


@router.post("/optimization/experiments")
async def create_experiment(body: CreateExperimentRequest, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        svc = ABTestingService(s)
        exp = svc.create_experiment(body.name, body.target_engine, body.variant_a, body.variant_b)
        variants = {v.label: v.id for v in ABVariantRepository(s).list_for_experiment(exp.id)}
        return {"experiment_id": exp.id, "variant_ids": variants}

    return await session.run_sync(_impl)


@router.get("/optimization/experiments")
async def list_experiments(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        svc = ABTestingService(s)
        exp_repo = ABExperimentRepository(s)
        var_repo = ABVariantRepository(s)
        out = []
        for exp in exp_repo.list():
            out.append(_serialize_experiment(exp, var_repo.list_for_experiment(exp.id), svc))
        return {"experiments": out}

    return await session.run_sync(_impl)


@router.post("/optimization/experiments/variants/{variant_id}/impression")
async def record_impression(variant_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        await session.run_sync(lambda s: ABTestingService(s).record_impression(variant_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/variants/{variant_id}/conversion")
async def record_conversion(variant_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        await session.run_sync(lambda s: ABTestingService(s).record_conversion(variant_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/{experiment_id}/conclude")
async def conclude_experiment(experiment_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        svc = ABTestingService(s)
        exp = svc.conclude(experiment_id)
        variants = ABVariantRepository(s).list_for_experiment(exp.id)
        return _serialize_experiment(exp, variants, svc)

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg else 409
        raise HTTPException(status_code=code, detail=msg)


# Declare the literal-segment activate route BEFORE the {prompt_name:path} routes
# to prevent the :path converter from capturing "versions/{version_id}/activate".
@router.post("/optimization/prompts/versions/{version_id}/activate")
async def activate_prompt_version(version_id: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_version(PromptEvolver(s).activate(version_id))
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/optimization/prompts/{prompt_name:path}/versions")
async def list_prompt_versions(prompt_name: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    versions = await session.run_sync(
        lambda s: PromptVersionRepository(s).list_for_prompt(prompt_name)
    )
    return {"versions": [_serialize_version(v) for v in versions]}


@router.post("/optimization/prompts/{prompt_name:path}/seed")
async def seed_prompt(prompt_name: str, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize_version(PromptEvolver(s).seed_from_disk(prompt_name))
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
