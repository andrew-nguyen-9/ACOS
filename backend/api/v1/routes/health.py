import logging
import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from backend.database import get_async_session
from backend.config import get_settings
from backend.models.optimization import PromptVersion
from backend.services import integrity
from backend.services.ollama_client import OllamaClient
from backend.services.system_status import collect

router = APIRouter(prefix="/health", tags=["health"])

_REQUIRED_MODELS = ["qwen3:8b", "nomic-embed-text"]


@lru_cache
def _migration_head() -> str:
    """Alembic head from the migration *scripts*, not the DB's stamped rev.

    The app provisions schema via Base.metadata.create_all (database.py), so the
    DB never stamps alembic_version — the meaningful "what schema does this build
    expect" answer is the script-directory head. Memoized: it can't change at
    runtime. Returns "unknown" rather than raising if the migration scripts
    aren't on disk (e.g. a packaged sidecar that didn't bundle them) — a metadata
    field must never 500 the health endpoint.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        repo_root = Path(__file__).resolve().parents[4]
        cfg = Config(str(repo_root / "alembic.ini"))
        return ScriptDirectory.from_config(cfg).get_current_head() or "unknown"
    except Exception:
        logging.getLogger(__name__).debug("migration head unavailable", exc_info=True)
        return "unknown"


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


@router.get("/version")
async def health_version(session: AsyncSession = Depends(get_async_session)) -> dict:
    """The reproducibility tuple for this build (Phase 14.1).

    One place answering "what exactly is this": app semver + model tags + active
    prompt-versions + migration head. A reproducible (seed, inputs, prompt, model)
    run is only verifiable against a pinned version surface.
    """
    settings = get_settings()

    def _active_prompts(s: Session) -> list[dict]:
        rows = s.execute(
            select(PromptVersion.prompt_name, PromptVersion.version).where(
                PromptVersion.is_active.is_(True)
            )
        ).all()
        return [{"prompt_name": name, "version": ver} for name, ver in rows]

    prompt_versions = await session.run_sync(_active_prompts)
    return {
        "app_version": settings.app_version,
        "model": {
            "generator": settings.default_model,
            "embedder": settings.embedding_model,
        },
        "prompt_versions": prompt_versions,
        "migration_head": _migration_head(),
    }


@router.get("/integrity")
async def health_integrity(session: AsyncSession = Depends(get_async_session)) -> dict:
    """On-demand deep integrity checks (can be slow on large DBs)."""
    settings = get_settings()

    # ponytail: the Chroma reconcile runs inside run_sync, holding the async DB
    # connection for the duration — acceptable on this on-demand deep-check route;
    # not worth splitting the Chroma probe out of the DB greenlet for one endpoint.
    def _impl(s: Session) -> dict:
        chroma_result: dict
        try:
            from backend.rag.chroma_client import get_chroma_manager

            chroma = get_chroma_manager(settings.chroma_db_path)
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
    from backend.rag.chroma_client import get_chroma_manager

    try:
        get_chroma_manager(settings.chroma_db_path).init_all_collections()
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
