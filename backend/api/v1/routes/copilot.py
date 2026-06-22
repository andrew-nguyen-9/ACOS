from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
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
def copilot_chat(
    body: ChatRequest, session: Session = Depends(get_session)
) -> dict:
    engine = _build_copilot(session)
    return engine.chat(body.message, conversation_history=body.conversation_history)


@router.get("/copilot/intents")
def list_intents() -> dict:
    return {"intents": sorted(_VALID_INTENTS)}
