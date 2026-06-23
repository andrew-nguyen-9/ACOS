"""Phase 9 Strategy API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session as get_db
from backend.models.strategy import (
    ApplicationPriority,
    ApplicationSuggestion,
    EnrichCorpusRequest,
    OutcomeReport,
    PrioritizeRequest,
    ResumeStrategyRequest,
    RoleFitRequest,
    RoleFitScore,
    ResumeStrategyRecommendation,
    SuggestionRequest,
)
from backend.services.strategy.application_strategy import ApplicationStrategyEngine
from backend.services.strategy.application_suggestion import ApplicationSuggestionEngine
from backend.services.strategy.career_path_simulator import CareerPathSimulator
from backend.services.strategy.corpus_scraper import CorpusScraper
from backend.services.strategy.outcome_learner import OutcomeLearner
from backend.services.strategy.resume_strategy_selector import ResumeStrategySelector
from backend.services.strategy.role_fit_scorer import RoleFitScorer
from backend.services.strategy.skill_gap_forecaster import SkillGapForecaster

logger = logging.getLogger(__name__)
router = APIRouter(tags=["strategy"])


@router.post("/strategy/role-fit", response_model=RoleFitScore)
async def role_fit(req: RoleFitRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return await db.run_sync(lambda s: RoleFitScorer(s).score(req.jd_text))


@router.get("/strategy/career-paths")
async def career_paths(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await db.run_sync(lambda s: CareerPathSimulator(s).simulate_all())


@router.post("/strategy/prioritize", response_model=list[ApplicationPriority])
async def prioritize(req: PrioritizeRequest, db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await db.run_sync(lambda s: ApplicationStrategyEngine(s).prioritize(req.jobs))


@router.post("/strategy/suggestion", response_model=ApplicationSuggestion)
async def suggestion(req: SuggestionRequest, db: AsyncSession = Depends(get_db)) -> dict:
    # Recommend-only (ADR-012): composes fit + resume + tone + interview outlook.
    return await db.run_sync(lambda s: ApplicationSuggestionEngine(s).suggest(req.jd_text))


@router.get("/strategy/skill-gaps")
async def skill_gaps(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await db.run_sync(lambda s: SkillGapForecaster(s).forecast())


@router.get("/strategy/resume-recommendation", response_model=ResumeStrategyRecommendation)
async def resume_recommendation(jd_text: str, db: AsyncSession = Depends(get_db)) -> dict:
    if len(jd_text) < 50:
        raise HTTPException(status_code=422, detail="jd_text must be at least 50 characters")
    return await db.run_sync(lambda s: ResumeStrategySelector(s).recommend(jd_text))


@router.post("/strategy/resume-recommendation/apply")
async def apply_resume_recommendation(req: ResumeStrategyRequest, db: AsyncSession = Depends(get_db)) -> dict:
    # ponytail: two-step gate — this endpoint confirms approval intent; actual generation
    # delegates to existing resume generation flow via its own endpoint
    recommendation = await db.run_sync(lambda s: ResumeStrategySelector(s).recommend(req.jd_text))
    return {
        "status": "pending_user_confirmation",
        "recommendation": recommendation,
        "message": "Recommendation noted. Submit to POST /resume/generate with template override to execute.",
    }


@router.post("/strategy/enrich-corpus")
async def enrich_corpus(req: EnrichCorpusRequest, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        import chromadb  # type: ignore[import]
        from backend.config import get_settings
        settings = get_settings()
        client = chromadb.PersistentClient(path=settings.chroma_db_path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"ChromaDB unavailable: {exc}") from exc

    scraper = CorpusScraper(client)
    return scraper.enrich(urls=req.urls, max_per_domain=req.max_per_domain)


@router.get("/analytics/outcomes", response_model=OutcomeReport)
async def outcomes_report(db: AsyncSession = Depends(get_db)) -> dict:
    return await db.run_sync(lambda s: OutcomeLearner(s).outcome_report())
