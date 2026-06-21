from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.docx_exporter import ResumeDOCXExporter
from backend.services.resume.evidence_selector import EvidenceSelector
from backend.services.resume.generator import ResumeGenerator
from backend.services.resume.templates import TEMPLATE_NAMES

router = APIRouter(tags=["resume"])

_VALID_TEMPLATES = set(TEMPLATE_NAMES)


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
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)
    selector = EvidenceSelector(retriever, reranker)
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
def generate_resume(
    body: GenerateRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template: '{body.template_name}'. Valid options: {TEMPLATE_NAMES}",
        )
    settings = get_settings()
    gen, _ = _build_deps(settings, session)
    try:
        return gen.generate(
            body.job_description, body.template_name, body.application_id,
            company=body.company, job_title=body.job_title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/resume/generate/download")
def generate_resume_docx(
    body: GenerateRequest,
    session: Session = Depends(get_session),
) -> Response:
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template: '{body.template_name}'. Valid options: {TEMPLATE_NAMES}",
        )
    settings = get_settings()
    gen, exporter = _build_deps(settings, session)
    try:
        result = gen.generate(
            body.job_description, body.template_name, body.application_id,
            company=body.company, job_title=body.job_title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    docx_bytes = exporter.export(result["content_json"], body.template_name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=resume.docx"},
    )
