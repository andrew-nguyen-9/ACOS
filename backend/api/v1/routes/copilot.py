from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.api.v1.sse import sse_token_stream
from backend.config import get_settings
from backend.database import get_async_session
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.fallback import KeywordFallback
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.observability import log_operation
from backend.services.copilot.engine import CopilotEngine
from backend.services.ollama_client import OllamaClient
from backend.services.rag.service import RAG_MODEL, RAG_SYSTEM, RAGService

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
    chroma = get_chroma_manager(settings.chroma_db_path)
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


@router.post("/copilot/chat/stream")
async def copilot_chat_stream(
    request: Request,
    body: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Stream a copilot answer token-by-token over SSE (Phase 12.4).

    Retrieval + prompt assembly run synchronously inside ``run_sync`` (the 12.2
    boundary); only the LLM generation streams. Completion is logged at stream end
    and skipped if the client disconnects mid-stream — so a cancelled generation is
    never recorded as a finished turn. (Copilot chat persists no result row; the
    same hook is where a streamed *persisting* endpoint would write, with the
    session still open — see sse_token_stream.)
    """
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)

    def _prepare(s: Session) -> tuple[str | None, dict]:
        engine = _build_copilot(s)
        return engine.prepare(body.message, body.conversation_history)

    prompt, base = await session.run_sync(_prepare)

    async def _tokens():
        if prompt is None:
            ready = base.get("response", "")  # fallback/degraded: the answer is ready
            if ready:
                yield ready  # don't frame an empty delta → blank bubble
            return
        async for delta in ollama.generate_stream(
            model=RAG_MODEL, prompt=prompt, temperature=0.3, system=RAG_SYSTEM
        ):
            yield delta

    async def _on_complete(_full: str) -> None:
        log_operation("copilot_chat_stream", intent=base.get("intent", ""))

    async def _body():
        # Leading non-token event: citations/confidence are known up front (from
        # retrieval), so the UI can render them while the answer still streams.
        meta = {k: base.get(k) for k in ("intent", "confidence", "citations", "evidence_count")}
        yield f"data: {json.dumps({'meta': meta})}\n\n"
        async for event in sse_token_stream(request, _tokens(), on_complete=_on_complete):
            yield event

    return StreamingResponse(_body(), media_type="text/event-stream")


@router.get("/copilot/intents")
def list_intents() -> dict:
    return {"intents": sorted(_VALID_INTENTS)}
