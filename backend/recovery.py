"""Corruption recovery mode (Phase 11.4).

A cheap startup probe (``PRAGMA quick_check`` — not the slow full
``integrity_check``, to protect the cold-start budget) runs after init_db. If it
fails, the app enters READONLY_RECOVERY instead of crashing: a middleware turns
mutating requests into 503s while leaving reads, /recovery/status, and
/backup/restore available so the user can roll back to a snapshot.

# ponytail: module-global flag — ACOS is a single-process local app (ADR-001),
# so there is no multi-worker state to coordinate.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
# Endpoints that must keep working in recovery mode (the way out + diagnostics).
_SAFE_PREFIXES = ("/api/v1/recovery", "/api/v1/backup/restore", "/api/v1/health")


class RecoveryState:
    def __init__(self) -> None:
        self.readonly = False
        self.reason: str | None = None

    def enter(self, reason: str) -> None:
        self.readonly = True
        self.reason = reason
        logger.error("Entering READONLY_RECOVERY mode: %s", reason)

    def clear(self) -> None:
        self.readonly = False
        self.reason = None


RECOVERY = RecoveryState()


def probe_integrity(session: Session) -> bool:
    """Cheap startup integrity probe. True if the DB looks intact."""
    try:
        row = session.execute(text("PRAGMA quick_check")).first()
        return bool(row) and row[0] == "ok"
    except Exception:
        # Log so a spurious recovery lockout (e.g. a code/migration bug, not real
        # corruption) is traceable rather than a silent generic "probe failed".
        logger.exception("integrity probe raised")
        return False


def maybe_enter_recovery(session: Session) -> bool:
    """Probe the DB; enter recovery mode on failure. Returns True if degraded."""
    if not probe_integrity(session):
        RECOVERY.enter("startup integrity probe failed (PRAGMA quick_check)")
        return True
    return False


def check_interrupted_restore(backups_dir: str | Path) -> bool:
    """A restore-in-progress sentinel means a previous restore died mid-swap;
    enter recovery so the user can re-run the restore (DB/Chroma may be split)."""
    from backend.services.backup.restore import SENTINEL_NAME

    sentinel = Path(backups_dir) / SENTINEL_NAME
    if not sentinel.is_file():
        return False
    try:
        data = json.loads(sentinel.read_text())
    except (OSError, json.JSONDecodeError):
        data = {}
    RECOVERY.enter(
        f"interrupted restore detected; auto restore point: {data.get('pre_restore')}"
    )
    return True


class ReadonlyRecoveryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if RECOVERY.readonly and request.method in _MUTATING:
            path = request.url.path
            if not any(path.startswith(p) for p in _SAFE_PREFIXES):
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "ACOS is in read-only recovery mode",
                        "reason": RECOVERY.reason,
                        "recover_via": "/api/v1/backup/restore",
                    },
                )
        return await call_next(request)
