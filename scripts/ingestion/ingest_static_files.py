#!/usr/bin/env python
"""Bulk-ingest all files from .static_files/ into the ACOS knowledge base."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.database import SessionLocal
from backend.ingestion.entity_extractor import EntityExtractor
from backend.ingestion.pipeline import IngestionPipeline
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_STATIC = Path(__file__).parent.parent.parent / ".static_files"
_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    indexer = RAGIndexer(chroma, embedder)
    extractor = EntityExtractor(ollama if ollama.is_available() else None)

    files = [f for f in _STATIC.rglob("*") if f.suffix.lower() in _EXTENSIONS]
    logger.info("found %d files to ingest from %s", len(files), _STATIC)

    ok = 0
    failed = 0
    with SessionLocal() as session:
        kg_svc = KnowledgeGraphService(session)
        pipeline = IngestionPipeline(
            session=session,
            kg_service=kg_svc,
            indexer=indexer,
            entity_extractor=extractor,
            allowed_dirs=[str(_STATIC)],
        )
        for f in files:
            try:
                doc_id = pipeline.ingest(str(f))
                logger.info("ingested %s → %s", f.name, doc_id)
                ok += 1
            except Exception as exc:
                logger.error("failed to ingest %s: %s", f, exc)
                failed += 1
        session.commit()

    logger.info("ingestion complete: %d ok, %d failed", ok, failed)


if __name__ == "__main__":
    main()
