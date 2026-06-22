from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.repositories.resume import ResumeRepository
from backend.services.cover_letter.docx_exporter import CoverLetterDOCXExporter
from backend.services.cover_letter.generator import CoverLetterGenerator, LENGTH_TARGETS
from backend.services.cover_letter.voice_modeler import VoiceModeler
from backend.services.ollama_client import OllamaClient
from backend.services.profile.contact_loader import default_contact_path, load_contact
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.evidence_selector import EvidenceSelector

router = APIRouter(tags=["cover_letter"])

_VALID_LENGTHS = set(LENGTH_TARGETS)


class GenerateCLRequest(BaseModel):
    job_description: str
    company: str = ""
    job_title: str = ""
    length_target: str = "medium"
    application_id: str | None = None
    resume_id: str | None = None
    # RCL-003 tone dial: 0 = Traditional, 1 = Bold. Omitted → learned voice only.
    tone: float | None = Field(default=None, ge=0.0, le=1.0)


class LearnVoiceRequest(BaseModel):
    texts: list[str]


def _build_cl_deps(
    settings: Settings, session: Session
) -> tuple[CoverLetterGenerator, CoverLetterDOCXExporter]:
    """Instantiate and wire all dependencies for cover letter generation."""
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder, session=session)
    reranker = Reranker()
    loader = PromptLoader()
    selector = EvidenceSelector(retriever, reranker)
    voice_modeler = VoiceModeler(ollama, loader, session)
    generator = CoverLetterGenerator(selector, voice_modeler, ollama, loader)
    exporter = CoverLetterDOCXExporter()
    return generator, exporter


@router.post("/cover-letter/generate")
async def generate_cover_letter(
    body: GenerateCLRequest, session: AsyncSession = Depends(get_async_session)
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

    def _impl(s: Session) -> dict[str, object]:
        generator, _ = _build_cl_deps(settings, s)
        resume_context: dict | None = None
        if body.resume_id:
            resume = ResumeRepository(s).get(body.resume_id)
            if resume is None:
                raise HTTPException(status_code=404, detail=f"Resume '{body.resume_id}' not found.")
            resume_context = resume.content_json.get("_resume_context")
        return generator.generate(
            body.job_description, body.company, body.job_title, body.length_target,
            resume_context=resume_context, tone=body.tone,
        )

    return await session.run_sync(_impl)


@router.post("/cover-letter/generate/download")
async def generate_cover_letter_docx(
    body: GenerateCLRequest, session: AsyncSession = Depends(get_async_session)
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

    def _impl(s: Session) -> dict:
        generator, exporter = _build_cl_deps(settings, s)
        resume_context = None
        if body.resume_id:
            resume = ResumeRepository(s).get(body.resume_id)
            if resume is None:
                raise HTTPException(status_code=404, detail=f"Resume '{body.resume_id}' not found.")
            resume_context = resume.content_json.get("_resume_context")
        result = generator.generate(
            body.job_description, body.company, body.job_title, body.length_target,
            resume_context=resume_context,
        )
        return {"text": result["text"], "exporter": exporter}

    payload = await session.run_sync(_impl)
    contact = load_contact(default_contact_path())
    docx_bytes = payload["exporter"].export(
        payload["text"], body.job_title, body.company, contact_info=contact
    )
    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": "attachment; filename=cover_letter.docx"},
    )


@router.post("/cover-letter/learn-voice")
async def learn_voice(
    body: LearnVoiceRequest, session: AsyncSession = Depends(get_async_session)
) -> dict[str, object]:
    """Extract a writing voice profile from the supplied cover letter texts."""
    settings = get_settings()

    def _impl(s: Session) -> dict[str, object]:
        ollama = OllamaClient(base_url=settings.ollama_base_url)
        loader = PromptLoader()
        modeler = VoiceModeler(ollama, loader, s)
        return modeler.learn(body.texts)

    return await session.run_sync(_impl)
