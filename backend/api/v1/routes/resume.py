from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
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


def _build_deps(settings: object, session: Session) -> tuple[ResumeGenerator, ResumeDOCXExporter]:
    ollama = OllamaClient(base_url=settings.ollama_base_url)  # type: ignore[union-attr]
    embedder = Embedder(ollama, model=settings.embedding_model)  # type: ignore[union-attr]
    chroma = ChromaManager(path=settings.chroma_db_path)  # type: ignore[union-attr]
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
    return gen.generate(body.job_description, body.template_name, body.application_id)


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
    result = gen.generate(body.job_description, body.template_name, body.application_id)
    docx_bytes = exporter.export(result["content_json"], body.template_name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=resume.docx"},
    )
