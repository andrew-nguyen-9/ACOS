from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.services.maintenance.advisor import MaintenanceAdvisor
from backend.services.maintenance.executor import MaintenanceExecutor, NotApprovedError

router = APIRouter(tags=["maintenance"])


class SuggestionRef(BaseModel):
    suggestion_id: str


def _serialize(s: MaintenanceSuggestion) -> dict:
    return {
        "id": s.id, "type": s.type, "reason": s.reason,
        "payload": json.loads(s.payload_json) if s.payload_json else None,
        "status": s.status, "snapshot_id": s.snapshot_id,
        "result": json.loads(s.result_json) if s.result_json else None,
        "created_at": s.created_at, "executed_at": s.executed_at,
    }


def _build_executor(session: Session) -> MaintenanceExecutor:
    # Indexer is only used by reindex/embedding_refresh; building it is cheap
    # (ChromaManager defers the chromadb import until a collection is touched).
    from backend.rag.chroma_client import ChromaManager
    from backend.rag.embedder import Embedder
    from backend.rag.indexer import RAGIndexer
    from backend.services.ollama_client import OllamaClient

    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    return MaintenanceExecutor(session, indexer=RAGIndexer(chroma, embedder))


@router.post("/maintenance/generate")
def generate_suggestions(session: Session = Depends(get_session)) -> dict:
    created = MaintenanceAdvisor(session).suggest()
    return {"created": len(created), "suggestion_ids": [s.id for s in created]}


@router.get("/maintenance/suggestions")
def list_suggestions(
    status: str | None = Query(default=None), session: Session = Depends(get_session)
) -> dict:
    q = session.query(MaintenanceSuggestion)
    if status:
        q = q.filter(MaintenanceSuggestion.status == status)
    return {"suggestions": [_serialize(s) for s in q.all()]}


@router.post("/maintenance/approve")
def approve(body: SuggestionRef, session: Session = Depends(get_session)) -> dict:
    try:
        s = MaintenanceExecutor(session).approve(body.suggestion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(s)


@router.post("/maintenance/dismiss")
def dismiss(body: SuggestionRef, session: Session = Depends(get_session)) -> dict:
    try:
        s = MaintenanceExecutor(session).dismiss(body.suggestion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(s)


@router.post("/maintenance/execute")
def execute(body: SuggestionRef, session: Session = Depends(get_session)) -> dict:
    try:
        s = _build_executor(session).execute(body.suggestion_id)
    except NotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return _serialize(s)


@router.get("/maintenance/audit")
def list_audit(limit: int = 100, session: Session = Depends(get_session)) -> dict:
    rows = (
        session.query(MaintenanceAudit)
        .order_by(MaintenanceAudit.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "audit": [
            {
                "id": a.id, "suggestion_id": a.suggestion_id, "event": a.event,
                "detail": json.loads(a.detail_json) if a.detail_json else None,
                "actor": a.actor, "created_at": a.created_at,
            }
            for a in rows
        ]
    }
