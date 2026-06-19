from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_session
from backend.config import get_settings
from backend.services.ollama_client import OllamaClient

router = APIRouter(prefix="/health", tags=["health"])

_REQUIRED_MODELS = ["qwen3:8b", "nomic-embed-text"]


@router.get("")
def health(session: Session = Depends(get_session)) -> JSONResponse:
    try:
        session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    http_status = 200 if db_status == "connected" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if db_status == "connected" else "degraded",
            "db": db_status,
            "version": get_settings().app_version,
        },
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
