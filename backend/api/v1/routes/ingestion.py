from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.ingestion.entity_extractor import EntityExtractor
from backend.ingestion.pipeline import IngestionPipeline
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

router = APIRouter(tags=["ingestion"])

_ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


@router.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Accept a file upload, run the ingestion pipeline, return the document ID."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {suffix!r}. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        from backend.ingestion.security import sanitize_filename
        safe_name = sanitize_filename(file.filename)
        dest = (Path(tmpdir) / safe_name).resolve()
        if not str(dest).startswith(str(Path(tmpdir).resolve()) + os.sep):
            raise HTTPException(status_code=400, detail="Invalid filename")
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        ollama = OllamaClient(base_url=settings.ollama_base_url)
        embedder = Embedder(ollama, model=settings.embedding_model)
        chroma = get_chroma_manager(settings.chroma_db_path)
        indexer = RAGIndexer(chroma, embedder)
        extractor = EntityExtractor(
            ollama if ollama.is_available() else None
        )

        def _impl(s: Session) -> str:
            pipeline = IngestionPipeline(
                session=s,
                kg_service=KnowledgeGraphService(s),
                indexer=indexer,
                entity_extractor=extractor,
                allowed_dirs=[tmpdir],
            )
            return pipeline.ingest(str(dest))

        try:
            doc_id = await session.run_sync(_impl)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "document_id": doc_id}
