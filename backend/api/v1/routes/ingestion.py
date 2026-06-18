from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.ingestion.entity_extractor import EntityExtractor
from backend.ingestion.pipeline import IngestionPipeline
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

router = APIRouter(tags=["ingestion"])

_ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


@router.post("/ingest")
def ingest_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
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
        # Sanitize filename — take only the basename, strip path separators
        safe_name = Path(file.filename or "upload").name
        if not safe_name or safe_name in (".", ".."):
            safe_name = "upload"
        dest = (Path(tmpdir) / safe_name).resolve()
        # Verify dest is inside tmpdir
        if not str(dest).startswith(str(Path(tmpdir).resolve()) + os.sep):
            raise HTTPException(status_code=400, detail="Invalid filename")
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        ollama = OllamaClient(base_url=settings.ollama_base_url)
        embedder = Embedder(ollama, model=settings.embedding_model)
        chroma = ChromaManager(path=settings.chroma_db_path)
        indexer = RAGIndexer(chroma, embedder)
        kg_svc = KnowledgeGraphService(session)
        extractor = EntityExtractor(
            ollama if ollama.is_available() else None
        )

        pipeline = IngestionPipeline(
            session=session,
            kg_service=kg_svc,
            indexer=indexer,
            entity_extractor=extractor,
            allowed_dirs=[tmpdir],
        )
        try:
            doc_id = pipeline.ingest(str(dest))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "document_id": doc_id}
