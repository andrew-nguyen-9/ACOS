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
