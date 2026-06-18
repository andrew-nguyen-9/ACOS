from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.ollama_client import OllamaClient
from backend.services.rag.service import RAGService

router = APIRouter(tags=["rag"])


class QueryRequest(BaseModel):
    query: str
    intent: str = "knowledge_lookup"


@router.post("/rag/query")
def rag_query(body: QueryRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    svc = RAGService(retriever, reranker, ollama if ollama.is_available() else None)
    return svc.query(body.query, intent=body.intent)
