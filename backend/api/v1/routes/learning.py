from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
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
def record_outcome(
    body: RecordOutcomeRequest, session: Session = Depends(get_session)
) -> dict:
    if body.signal_type not in _VALID_SIGNALS:
        raise HTTPException(
            status_code=422, detail=f"Invalid signal_type '{body.signal_type}'"
        )
    ranker = OutcomeRanker(session)
    try:
        return ranker.record_outcome(
            application_id=body.application_id,
            signal_type=body.signal_type,
            resume_id=body.resume_id,
            template_used=body.template_used,
            ats_score=body.ats_score,
            industry=body.industry,
            position_type=body.position_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=422, detail="Invalid application_id: application not found")


@router.post("/learning/reindex")
def trigger_reindex(
    only_changed: bool = False, session: Session = Depends(get_session)
) -> dict:
    settings = get_settings()
    repo = SystemConfigRepository(session)
    embedding_model = repo.get_value("embedding_model") or settings.embedding_model
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    indexer = RAGIndexer(chroma, embedder)
    count = indexer.index_all(session, only_changed=only_changed)
    return {"status": "ok", "indexed": count}


@router.get("/learning/rankings")
def get_rankings(session: Session = Depends(get_session)) -> dict:
    ranker = OutcomeRanker(session)
    return {"template_rankings": ranker.get_template_rankings()}


@router.get("/learning/report")
def get_effectiveness_report(session: Session = Depends(get_session)) -> dict:
    ranker = OutcomeRanker(session)
    return {
        "template_rankings": ranker.get_template_rankings(),
        "ats_vs_outcome": ranker.get_ats_vs_outcome_correlation(),
    }
