from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
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
    from backend.rag.chroma_client import get_chroma_manager
    from backend.rag.embedder import Embedder
    from backend.rag.indexer import RAGIndexer
    from backend.services.ollama_client import OllamaClient

    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    return MaintenanceExecutor(session, indexer=RAGIndexer(chroma, embedder))


@router.post("/maintenance/generate")
async def generate_suggestions(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        created = MaintenanceAdvisor(s).suggest()
        return {"created": len(created), "suggestion_ids": [c.id for c in created]}

    return await session.run_sync(_impl)


@router.get("/maintenance/suggestions")
async def list_suggestions(
    status: str | None = Query(default=None), session: AsyncSession = Depends(get_async_session)
) -> dict:
    def _impl(s: Session) -> dict:
        q = s.query(MaintenanceSuggestion)
        if status:
            q = q.filter(MaintenanceSuggestion.status == status)
        return {"suggestions": [_serialize(row) for row in q.all()]}

    return await session.run_sync(_impl)


@router.post("/maintenance/approve")
async def approve(body: SuggestionRef, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize(MaintenanceExecutor(s).approve(body.suggestion_id))
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/maintenance/dismiss")
async def dismiss(body: SuggestionRef, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize(MaintenanceExecutor(s).dismiss(body.suggestion_id))
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/maintenance/execute")
async def execute(body: SuggestionRef, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        return await session.run_sync(
            lambda s: _serialize(_build_executor(s).execute(body.suggestion_id))
        )
    except NotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/maintenance/audit")
async def list_audit(limit: int = 100, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        rows = (
            s.query(MaintenanceAudit)
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

    return await session.run_sync(_impl)
