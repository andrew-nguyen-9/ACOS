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
from backend.services.cover_letter.docx_exporter import CoverLetterDOCXExporter
from backend.services.cover_letter.generator import CoverLetterGenerator, LENGTH_TARGETS
from backend.services.cover_letter.voice_modeler import VoiceModeler
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.evidence_selector import EvidenceSelector

router = APIRouter(tags=["cover_letter"])

_VALID_LENGTHS = set(LENGTH_TARGETS)


class GenerateCLRequest(BaseModel):
    job_description: str
    company: str
    job_title: str
    length_target: str = "medium"
    application_id: str | None = None


class LearnVoiceRequest(BaseModel):
    texts: list[str]


def _build_cl_deps(
    settings: Settings, session: Session
) -> tuple[CoverLetterGenerator, CoverLetterDOCXExporter]:
    """Instantiate and wire all dependencies for cover letter generation."""
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    selector = EvidenceSelector(retriever, reranker)
    voice_modeler = VoiceModeler(ollama, loader, session)
    generator = CoverLetterGenerator(selector, voice_modeler, ollama, loader)
    exporter = CoverLetterDOCXExporter()
    return generator, exporter


@router.post("/cover-letter/generate")
def generate_cover_letter(
    body: GenerateCLRequest, session: Session = Depends(get_session)
) -> dict[str, object]:
    """Generate a cover letter and return the text payload."""
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid length_target '{body.length_target}'. "
                f"Valid: {sorted(_VALID_LENGTHS)}"
            ),
        )
    settings = get_settings()
    generator, _ = _build_cl_deps(settings, session)
    return generator.generate(
        body.job_description, body.company, body.job_title, body.length_target
    )


@router.post("/cover-letter/generate/download")
def generate_cover_letter_docx(
    body: GenerateCLRequest, session: Session = Depends(get_session)
) -> Response:
    """Generate a cover letter and return it as a DOCX file download."""
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid length_target '{body.length_target}'. "
                f"Valid: {sorted(_VALID_LENGTHS)}"
            ),
        )
    settings = get_settings()
    generator, exporter = _build_cl_deps(settings, session)
    result = generator.generate(
        body.job_description, body.company, body.job_title, body.length_target
    )
    docx_bytes = exporter.export(result["text"], body.job_title, body.company)
    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": "attachment; filename=cover_letter.docx"},
    )


@router.post("/cover-letter/learn-voice")
def learn_voice(
    body: LearnVoiceRequest, session: Session = Depends(get_session)
) -> dict[str, object]:
    """Extract a writing voice profile from the supplied cover letter texts."""
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    loader = PromptLoader()
    modeler = VoiceModeler(ollama, loader, session)
    return modeler.learn(body.texts)
