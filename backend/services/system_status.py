"""Aggregated subsystem health (Phase 11.1).

One surface combining DB / Chroma / Ollama / embedding-version state so
``/health`` and the UI banner can show partial degradation instead of a binary
up/down. Each probe is defensive: any error degrades that subsystem to ``down``
rather than crashing the health check.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services import integrity

_OK = "ok"
_DEGRADED = "degraded"
_DOWN = "down"


def _safe_bool(fn) -> bool:
    try:
        return bool(fn())
    except Exception:
        return False


@dataclass
class SystemStatus:
    db: str
    chroma: str
    ollama: str
    embedding: str

    @property
    def overall(self) -> str:
        states = (self.db, self.chroma, self.ollama, self.embedding)
        if _DOWN in states:
            return _DOWN
        if _DEGRADED in states:
            return _DEGRADED
        return _OK

    def as_dict(self) -> dict:
        return {**asdict(self), "overall": self.overall}


def collect(session: Session, chroma, ollama, embedding_model: str) -> SystemStatus:
    db = _OK if _safe_bool(lambda: session.execute(text("SELECT 1"))) else _DOWN
    chroma_state = _OK if _safe_bool(chroma.health_check) else _DOWN
    ollama_state = _OK if _safe_bool(ollama.is_available) else _DOWN

    try:
        emb = integrity.embedding_status(session, embedding_model)
        embedding_state = _OK if emb == "current" else _DEGRADED
    except Exception:
        embedding_state = _DOWN

    return SystemStatus(
        db=db, chroma=chroma_state, ollama=ollama_state, embedding=embedding_state
    )
