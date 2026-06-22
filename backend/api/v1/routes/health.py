import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_async_session
from backend.config import get_settings
from backend.services import integrity
from backend.services.ollama_client import OllamaClient
from backend.services.system_status import collect

router = APIRouter(prefix="/health", tags=["health"])

_REQUIRED_MODELS = ["qwen3:8b", "nomic-embed-text"]


class _ChromaLiveness:
    """Cheap Chroma probe for the hot /health path: directory existence only.

    # ponytail: avoids constructing a PersistentClient on every health ping.
    # The real heartbeat + reconciliation lives in /health/integrity.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def health_check(self) -> bool:
        return os.path.isdir(self._path)


@router.get("")
async def health(session: AsyncSession = Depends(get_async_session)) -> JSONResponse:
    settings = get_settings()

    def _impl(s: Session) -> tuple[str, dict]:
        try:
            s.execute(text("SELECT 1"))
            db = "connected"
        except Exception:
            db = "error"
        subs = collect(
            s,
            _ChromaLiveness(settings.chroma_db_path),
            OllamaClient(base_url=settings.ollama_base_url, timeout=2),
            settings.embedding_model,
        ).as_dict()
        return db, subs

    db_status, subsystems = await session.run_sync(_impl)

    http_status = 200 if db_status == "connected" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if db_status == "connected" else "degraded",
            "db": db_status,
            "version": settings.app_version,
            "subsystems": subsystems,
        },
    )


@router.get("/integrity")
async def health_integrity(session: AsyncSession = Depends(get_async_session)) -> dict:
    """On-demand deep integrity checks (can be slow on large DBs)."""
    settings = get_settings()

    def _impl(s: Session) -> dict:
        chroma_result: dict
        try:
            from backend.rag.chroma_client import ChromaManager

            chroma = ChromaManager(path=settings.chroma_db_path)
            chroma_result = integrity.chroma_reconcile(s, chroma)
        except Exception as exc:
            chroma_result = {"reconciled": False, "reason": f"chroma unavailable: {exc}"}

        return {
            "sqlite_integrity": integrity.sqlite_integrity(s),
            "foreign_key_violations": integrity.foreign_key_check(s),
            "chroma": chroma_result,
            "embedding": integrity.embedding_status(s, settings.embedding_model),
        }

    return await session.run_sync(_impl)


@router.get("/warmup")
def health_warmup() -> JSONResponse:
    """Force lazy Chroma init so connection errors surface on demand.

    Chroma's client + chromadb import are deferred for fast startup (11.3); this
    probe materializes them by creating all collections.
    """
    settings = get_settings()
    from backend.rag.chroma_client import ChromaManager

    try:
        ChromaManager(path=settings.chroma_db_path).init_all_collections()
        return JSONResponse(status_code=200, content={"warmed": True, "chroma": "ok"})
    except Exception as exc:
        logging.getLogger(__name__).exception("Chroma warmup failed")
        return JSONResponse(
            status_code=503, content={"warmed": False, "chroma": str(exc)}
        )


@router.get("/ollama")
def health_ollama() -> dict:
    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url, timeout=5)
    available = client.is_available()
    models = client.list_models() if available else []
    # Match on prefix so "nomic-embed-text:latest" satisfies "nomic-embed-text".
    present = {m.split(":")[0] for m in models}
    missing = [m for m in _REQUIRED_MODELS if m.split(":")[0] not in present]
    degraded = (not available) or bool(missing)
    return {
        "available": available,
        "models": models,
        "required_models": _REQUIRED_MODELS,
        "missing_models": missing,
        "degraded": degraded,
    }
