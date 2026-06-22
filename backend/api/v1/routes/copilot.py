from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.fallback import KeywordFallback
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.copilot.engine import CopilotEngine
from backend.services.ollama_client import OllamaClient
from backend.services.rag.service import RAGService

router = APIRouter(tags=["copilot"])

_VALID_INTENTS = {
    "resume_help",
    "cover_letter_help",
    "interview_prep",
    "job_fit_analysis",
    "career_advice",
    "knowledge_lookup",
}


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


def _build_copilot(session: Session) -> CopilotEngine:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    rag_svc = RAGService(
        retriever,
        reranker,
        ollama if ollama.is_available() else None,
        fallback=KeywordFallback(session),
    )
    return CopilotEngine(rag_svc)


@router.post("/copilot/chat")
async def copilot_chat(
    body: ChatRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    def _impl(s: Session) -> dict:
        engine = _build_copilot(s)
        return engine.chat(body.message, conversation_history=body.conversation_history)

    return await session.run_sync(_impl)


@router.get("/copilot/intents")
def list_intents() -> dict:
    return {"intents": sorted(_VALID_INTENTS)}
