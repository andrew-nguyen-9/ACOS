from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.repositories.question import AnswerRepository, QuestionRepository
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.questions.generator import QuestionGenerator
from backend.services.resume.evidence_selector import EvidenceSelector

router = APIRouter(tags=["questions"])

_VALID_LENGTHS = {"short", "medium", "long"}


class GenerateQuestionsRequest(BaseModel):
    job_description: str
    company: str = ""
    position: str = ""
    industry: str = ""
    tech_stack: str = ""
    application_id: str | None = None


class GenerateAnswerRequest(BaseModel):
    variables: dict[str, str] = {}
    application_id: str | None = None
    length_target: str = "medium"


class EditAnswerRequest(BaseModel):
    edited_text: str
    diff_summary: str | None = None


def _build_generator(settings: Settings, session: Session) -> QuestionGenerator:
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder, session=session)
    reranker = Reranker()
    loader = PromptLoader()
    selector = EvidenceSelector(retriever, reranker)
    return QuestionGenerator(ollama, loader, selector, session)


@router.post("/questions/generate")
async def generate_questions(
    body: GenerateQuestionsRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    def _impl(s: Session) -> dict:
        gen = _build_generator(get_settings(), s)
        return {
            "questions": gen.generate_questions(
                body.job_description,
                company=body.company,
                position=body.position,
                industry=body.industry,
                tech_stack=body.tech_stack,
                application_id=body.application_id,
            )
        }

    return await session.run_sync(_impl)


@router.post("/questions/{question_id}/answer")
async def generate_answer(
    question_id: str,
    body: GenerateAnswerRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(
            status_code=422, detail=f"Invalid length_target '{body.length_target}'"
        )

    def _impl(s: Session) -> dict:
        gen = _build_generator(get_settings(), s)
        return gen.generate_answer(
            question_id=question_id,
            variables=body.variables,
            application_id=body.application_id,
            length_target=body.length_target,
        )

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=422, detail="Invalid application_id: application not found")


@router.patch("/questions/{question_id}/answers/{answer_id}")
async def edit_answer(
    question_id: str,
    answer_id: str,
    body: EditAnswerRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    def _impl(s: Session) -> dict:
        gen = _build_generator(get_settings(), s)
        return gen.edit_answer(
            answer_id=answer_id,
            edited_text=body.edited_text,
            diff_summary=body.diff_summary,
        )

    try:
        return await session.run_sync(_impl)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/questions")
async def list_questions(
    category: str | None = None, session: AsyncSession = Depends(get_async_session)
) -> list[dict]:
    def _impl(s: Session) -> list[dict]:
        q_repo = QuestionRepository(s)
        questions = q_repo.get_by_category(category) if category else q_repo.list()
        return [
            {
                "id": q.id,
                "question_template": q.question_template,
                "category": q.category,
                "variables": q.variables,
            }
            for q in questions
        ]

    return await session.run_sync(_impl)


@router.get("/questions/{question_id}/answers")
async def list_answers(
    question_id: str, session: AsyncSession = Depends(get_async_session)
) -> list[dict]:
    def _impl(s: Session) -> list[dict]:
        q_repo = QuestionRepository(s)
        if q_repo.get(question_id) is None:
            raise HTTPException(status_code=404, detail="Question not found")
        a_repo = AnswerRepository(s)
        answers = a_repo.get_by_question(question_id)
        return [
            {
                "id": a.id,
                "original_answer": a.original_answer,
                "edited_answer": a.edited_answer,
                "confidence_level": a.confidence_level,
                "evidence_ids": a.evidence_ids,
                "created_at": a.created_at,
            }
            for a in answers
        ]

    return await session.run_sync(_impl)
