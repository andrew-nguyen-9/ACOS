"""
Standalone script to re-embed all documents into ChromaDB.
Run from repo root: python scripts/maintenance/reindex_all.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.database import SessionLocal, init_db
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.repositories.system_config import SystemConfigRepository
from backend.services.ollama_client import OllamaClient


def main() -> None:
    init_db()
    settings = get_settings()

    ollama = OllamaClient(base_url=settings.ollama_base_url)
    if not ollama.is_available():
        print(
            f"Warning: Ollama is not reachable at {settings.ollama_base_url}. "
            "Re-indexing requires Ollama to generate embeddings. "
            "Start Ollama and retry."
        )
        return

    with SessionLocal() as session:
        repo = SystemConfigRepository(session)
        embedding_model = repo.get_value("embedding_model") or settings.embedding_model
        embedder = Embedder(ollama, model=embedding_model)
        chroma = ChromaManager(path=settings.chroma_db_path)
        indexer = RAGIndexer(chroma, embedder)
        count = indexer.index_all(session)
        session.commit()

    print(f"Re-indexed {count} documents.")


if __name__ == "__main__":
    main()
