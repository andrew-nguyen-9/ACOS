from __future__ import annotations

from typing import NoReturn
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.repositories.optimization import (
    OptimizationProposalRepository, OptimizationLogRepository,
)
from backend.services.optimization.applier import Applier, ApprovalRequired
from backend.services.optimization.recommender import Recommender
from backend.services.optimization.loop import LearningLoop

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
def list_proposals(
    status: str | None = Query(default=None), session: Session = Depends(get_session)
) -> dict:
    repo = OptimizationProposalRepository(session)
    rows = repo.list_by_status(status) if status else repo.list()
    return {"proposals": [_serialize_proposal(p) for p in rows]}


@router.post("/optimization/proposals/generate")
def generate_proposals(session: Session = Depends(get_session)) -> dict:
    created = Recommender(session).generate_proposals()
    return {"created": len(created), "proposal_ids": [p.id for p in created]}


@router.post("/optimization/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        p = Applier(session).approve(proposal_id)
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)
    return _serialize_proposal(p)


@router.post("/optimization/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        p = Applier(session).reject(proposal_id)
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)
    return _serialize_proposal(p)


@router.post("/optimization/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        log = Applier(session).apply(proposal_id)
    except ApprovalRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_log(log)


@router.post("/optimization/proposals/{proposal_id}/revert")
def revert_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        log = Applier(session).revert(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _serialize_log(log)


@router.get("/optimization/logs")
def list_logs(limit: int = 50, session: Session = Depends(get_session)) -> dict:
    logs = OptimizationLogRepository(session).list_recent(limit=limit)
    return {"logs": [_serialize_log(l) for l in logs]}


@router.post("/optimization/loop/run")
def run_loop(session: Session = Depends(get_session)) -> dict:
    return LearningLoop(session).maybe_run()


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
def create_experiment(body: CreateExperimentRequest, session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    exp = svc.create_experiment(body.name, body.target_engine, body.variant_a, body.variant_b)
    variants = {v.label: v.id for v in ABVariantRepository(session).list_for_experiment(exp.id)}
    return {"experiment_id": exp.id, "variant_ids": variants}


@router.get("/optimization/experiments")
def list_experiments(session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    exp_repo = ABExperimentRepository(session)
    var_repo = ABVariantRepository(session)
    out = []
    for exp in exp_repo.list():
        out.append(_serialize_experiment(exp, var_repo.list_for_experiment(exp.id), svc))
    return {"experiments": out}


@router.post("/optimization/experiments/variants/{variant_id}/impression")
def record_impression(variant_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        ABTestingService(session).record_impression(variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/variants/{variant_id}/conversion")
def record_conversion(variant_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        ABTestingService(session).record_conversion(variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/{experiment_id}/conclude")
def conclude_experiment(experiment_id: str, session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    try:
        exp = svc.conclude(experiment_id)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg else 409
        raise HTTPException(status_code=code, detail=msg)
    variants = ABVariantRepository(session).list_for_experiment(exp.id)
    return _serialize_experiment(exp, variants, svc)


# Declare the literal-segment activate route BEFORE the {prompt_name:path} routes
# to prevent the :path converter from capturing "versions/{version_id}/activate".
@router.post("/optimization/prompts/versions/{version_id}/activate")
def activate_prompt_version(version_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        v = PromptEvolver(session).activate(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_version(v)


@router.get("/optimization/prompts/{prompt_name:path}/versions")
def list_prompt_versions(prompt_name: str, session: Session = Depends(get_session)) -> dict:
    repo = PromptVersionRepository(session)
    return {"versions": [_serialize_version(v) for v in repo.list_for_prompt(prompt_name)]}


@router.post("/optimization/prompts/{prompt_name:path}/seed")
def seed_prompt(prompt_name: str, session: Session = Depends(get_session)) -> dict:
    try:
        v = PromptEvolver(session).seed_from_disk(prompt_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_version(v)
