from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.repositories.system_config import SystemConfigRepository
from backend.services.learning.ranker import OutcomeRanker
from backend.services.ollama_client import OllamaClient

router = APIRouter(tags=["learning"])

_VALID_SIGNALS = {
    "no_response", "rejected", "phone_screen", "interview",
    "final_round", "offer", "accepted",
}


class RecordOutcomeRequest(BaseModel):
    application_id: str
    signal_type: str
    resume_id: str | None = None
    template_used: str | None = None
    ats_score: float | None = None
    industry: str | None = None
    position_type: str | None = None


@router.post("/learning/outcome")
async def record_outcome(
    body: RecordOutcomeRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    if body.signal_type not in _VALID_SIGNALS:
        raise HTTPException(
            status_code=422, detail=f"Invalid signal_type '{body.signal_type}'"
        )

    def _impl(s: Session) -> dict:
        return OutcomeRanker(s).record_outcome(
            application_id=body.application_id,
            signal_type=body.signal_type,
            resume_id=body.resume_id,
            template_used=body.template_used,
            ats_score=body.ats_score,
            industry=body.industry,
            position_type=body.position_type,
        )

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=422, detail="Invalid application_id: application not found")


@router.post("/learning/reindex")
async def trigger_reindex(
    only_changed: bool = False, session: AsyncSession = Depends(get_async_session)
) -> dict:
    settings = get_settings()

    def _impl(s: Session) -> int:
        repo = SystemConfigRepository(s)
        embedding_model = repo.get_value("embedding_model") or settings.embedding_model
        ollama = OllamaClient(base_url=settings.ollama_base_url)
        embedder = Embedder(ollama, model=embedding_model)
        chroma = get_chroma_manager(settings.chroma_db_path)
        indexer = RAGIndexer(chroma, embedder)
        return indexer.index_all(s, only_changed=only_changed)

    count = await session.run_sync(_impl)
    return {"status": "ok", "indexed": count}


@router.get("/learning/rankings")
async def get_rankings(session: AsyncSession = Depends(get_async_session)) -> dict:
    rankings = await session.run_sync(lambda s: OutcomeRanker(s).get_template_rankings())
    return {"template_rankings": rankings}


@router.get("/learning/report")
async def get_effectiveness_report(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        ranker = OutcomeRanker(s)
        return {
            "template_rankings": ranker.get_template_rankings(),
            "ats_vs_outcome": ranker.get_ats_vs_outcome_correlation(),
        }

    return await session.run_sync(_impl)
