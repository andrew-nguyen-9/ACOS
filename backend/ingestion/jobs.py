"""Background ingestion job state + worker (Phase 12.6 AC4).

Lives outside ``backend/api`` deliberately: the worker runs in the FastAPI
BackgroundTasks threadpool (off the event loop), so it uses a sync ``Session`` —
which the 12.2 boundary forbids inside request handlers but is correct here. The
route stays async and only enqueues this worker.
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import asdict, dataclass

from backend.config import get_settings
from backend.database import SessionLocal
from backend.ingestion.entity_extractor import EntityExtractor
from backend.ingestion.pipeline import IngestionPipeline
from backend.rag.chroma_client import get_chroma_manager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# ponytail: in-memory job map — single-process, single-user desktop app; a job
# queue / broker is YAGNI. Lost on restart, which is acceptable (re-upload).
JOBS: dict[str, "IngestJob"] = {}

TERMINAL = {"done", "failed"}

# Seam so the worker gets a FRESH session (the request's async session closes when
# the 202 returns). Tests patch this onto the in-memory test DB.
BACKGROUND_SESSION_FACTORY = SessionLocal


@dataclass
class IngestJob:
    id: str
    status: str  # queued | processing | done | failed
    filename: str
    document_id: str | None = None
    error: str | None = None

    def public(self) -> dict:
        d = asdict(self)
        d["job_id"] = d.pop("id")
        return d


def run_ingest_job(job_id: str, path: str, tmpdir: str) -> None:
    """Ingest *path* on a fresh session and update the job map.

    Runs sync in the BackgroundTasks threadpool. File-security validation already
    ran on the request thread before the 202; ``ingest_safe`` dead-letters any
    failure to ``ingestion_failures`` rather than raising.
    """
    job = JOBS[job_id]
    job.status = "processing"
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = get_chroma_manager(settings.chroma_db_path)
    extractor = EntityExtractor(ollama if ollama.is_available() else None)
    try:
        with BACKGROUND_SESSION_FACTORY() as session:  # type: ignore[operator]
            # 12.14: the background worker opens a raw session outside the request
            # dependencies, so bind the tenant here or every scoped write raises
            # TenantScopeError. Single-user/local → the default profile.
            from backend.services.tenancy import ensure_default_tenant, set_session_tenant

            set_session_tenant(session, ensure_default_tenant(session))
            # session passed so the indexer mirrors document text into FTS5 (12.7).
            indexer = RAGIndexer(chroma, embedder, session=session)
            pipeline = IngestionPipeline(
                session=session,
                kg_service=KnowledgeGraphService(session),
                indexer=indexer,
                entity_extractor=extractor,
                allowed_dirs=[tmpdir],
            )
            result = pipeline.ingest_safe(path)
            session.commit()
        if result["status"] == "ok":
            job.status = "done"
            job.document_id = result["document_id"]
        else:
            job.status = "failed"
            job.error = result.get("error", "ingestion failed")
    except Exception as exc:  # pragma: no cover - defensive; ingest_safe shouldn't raise
        logger.exception("run_ingest_job %s crashed", job_id)
        job.status = "failed"
        job.error = str(exc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
