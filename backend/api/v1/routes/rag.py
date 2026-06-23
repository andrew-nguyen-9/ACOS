from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.fallback import KeywordFallback
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.observability.metrics import MetricsStore
from backend.services.ollama_client import OllamaClient
from backend.services.rag.service import RAGService

router = APIRouter(tags=["rag"])


class QueryRequest(BaseModel):
    query: str
    intent: str = "knowledge_lookup"


@router.post("/rag/query")
async def rag_query(body: QueryRequest, session: AsyncSession = Depends(get_async_session)):
    settings = get_settings()
    ollama = OllamaClient(
        base_url=settings.ollama_base_url,
        num_thread=settings.ollama_num_thread,
        keep_alive=settings.ollama_keep_alive,
    )
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()

    def _impl(s: Session) -> dict:
        svc = RAGService(
            retriever,
            reranker,
            ollama if ollama.is_available() else None,
            fallback=KeywordFallback(s),
            embed_model=settings.embedding_model,
            session=s,  # FTS5 lexical leg (12.7)
        )
        result = svc.query(body.query, intent=body.intent)
        _emit_retrieval_metric(s, result)
        return result

    return await session.run_sync(_impl)


def _emit_retrieval_metric(session: Session, result: dict) -> None:
    """Best-effort: record mean top-5 evidence similarity for drift tracking.

    Only dense hits carry a meaningful similarity; lexical-only FTS5 hits report
    0.0 semantic similarity (12.7), so they're excluded — otherwise they'd depress
    the drift mean for a reason unrelated to embedding drift.
    """
    try:
        scores = [s for e in result.get("evidence", []) if (s := e.get("similarity_score", 0.0)) > 0][:5]
        if scores:
            MetricsStore(session).record(
                "retrieval_quality", sum(scores) / len(scores),
                {"degraded": result.get("degraded", False)},
            )
    except Exception:
        pass
