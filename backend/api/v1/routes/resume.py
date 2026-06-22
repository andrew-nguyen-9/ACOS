from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.flywheel.feedback import record_signal
from backend.services.observability.metrics import MetricsStore
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.docx_exporter import ResumeDOCXExporter
from backend.services.resume.evidence_selector import EvidenceSelector
from backend.services.resume.generator import ResumeGenerator
from backend.services.resume.templates import TEMPLATE_NAMES
from backend.services.profile.contact_loader import default_contact_path, load_contact

router = APIRouter(tags=["resume"])

_VALID_TEMPLATES = set(TEMPLATE_NAMES)


def _emit_ats_metric(session: Session, result: dict, template: str) -> None:
    """Best-effort: record the generated resume's ATS score for drift tracking.

    Telemetry must never fail a generation, so swallow any error.
    """
    try:
        score = result.get("ats_score", {}).get("overall_score")
        if score is not None:
            metric = MetricsStore(session).record("ats_score", float(score), {"template": template})
            # 12.10 flywheel emit: source-link the ATS score to its metric row.
            record_signal(
                session,
                entity_type="template",
                entity_id=template,
                signal_type="ats_score",
                value=float(score),
                source={"table": "metrics", "ids": [metric.id]},
            )
    except Exception:
        pass


class ATSRequest(BaseModel):
    resume_text: str
    job_description: str


class GenerateRequest(BaseModel):
    job_description: str
    template_name: str = "software"
    application_id: str | None = None
    company: str = ""
    job_title: str = ""


def _build_deps(settings: Settings, session: Session) -> tuple[ResumeGenerator, ResumeDOCXExporter]:
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)
    selector = EvidenceSelector(retriever, reranker, session=session)
    gen = ResumeGenerator(selector, extractor, scorer, ollama, loader, session)
    exporter = ResumeDOCXExporter()
    return gen, exporter


@router.post("/resume/analyze-ats")
def analyze_ats(body: ATSRequest) -> dict[str, object]:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)  # type: ignore[union-attr]
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)
    keywords = extractor.extract(body.job_description)
    score = scorer.score(body.resume_text, body.job_description, keywords)
    return {"keywords": keywords, "ats_score": score}


@router.post("/resume/generate")
async def generate_resume(
    body: GenerateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, object]:
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template: '{body.template_name}'. Valid options: {TEMPLATE_NAMES}",
        )
    settings = get_settings()

    def _impl(s: Session) -> dict:
        gen, _ = _build_deps(settings, s)
        result = gen.generate(
            body.job_description, body.template_name, body.application_id,
            company=body.company, job_title=body.job_title,
        )
        _emit_ats_metric(s, result, body.template_name)
        return result

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/resume/generate/download")
async def generate_resume_docx(
    body: GenerateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template: '{body.template_name}'. Valid options: {TEMPLATE_NAMES}",
        )
    settings = get_settings()

    def _impl(s: Session) -> dict:
        gen, exporter = _build_deps(settings, s)
        result = gen.generate(
            body.job_description, body.template_name, body.application_id,
            company=body.company, job_title=body.job_title,
        )
        return {"content_json": result["content_json"], "exporter": exporter}

    try:
        payload = await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    contact = load_contact(default_contact_path())
    docx_bytes = payload["exporter"].export(payload["content_json"], body.template_name, contact_info=contact)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=resume.docx"},
    )
