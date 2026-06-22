"""Data-integrity checks for SQLite + Chroma + embeddings (Phase 11.1).

All read-only. Surfaced via ``/health/integrity`` (on-demand, not per-request —
``PRAGMA integrity_check`` can be slow on large DBs).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.document import Document
from backend.models.system_config import SystemConfig
from backend.rag.collections import ALL_COLLECTION_NAMES


def sqlite_integrity(session: Session) -> str:
    """Return ``"ok"`` or the first problem reported by ``PRAGMA integrity_check``."""
    rows = session.execute(text("PRAGMA integrity_check")).fetchall()
    if not rows:
        return "unknown"
    return str(rows[0][0])


def foreign_key_check(session: Session) -> int:
    """Return the number of foreign-key violations (``PRAGMA foreign_key_check``)."""
    rows = session.execute(text("PRAGMA foreign_key_check")).fetchall()
    return len(rows)


def chroma_reconcile(session: Session, chroma) -> dict:
    """Reconcile SQLite document count against total Chroma vectors.

    # ponytail: a count comparison, not a per-id diff — enough to flag "vectors
    # missing/stale"; upgrade to id-level reconciliation only if drift is real.
    """
    sqlite_documents = session.query(Document).count()
    try:
        chroma_vectors = sum(chroma.count(name) for name in ALL_COLLECTION_NAMES)
    except Exception:
        return {
            "sqlite_documents": sqlite_documents,
            "chroma_vectors": None,
            "reconciled": False,
            "reason": "chroma unavailable",
        }
    reconciled = chroma_vectors >= sqlite_documents
    return {
        "sqlite_documents": sqlite_documents,
        "chroma_vectors": chroma_vectors,
        "reconciled": reconciled,
    }


def embedding_status(session: Session, configured_model: str) -> str:
    """Compare the configured embedding model against the recorded one.

    Returns ``current`` (match), ``stale`` (differs — re-embedding advisable),
    or ``unknown`` (nothing recorded yet). Never auto-rebuilds (see 11.4).
    """
    recorded = session.get(SystemConfig, "embedding_model")
    if recorded is None or not recorded.value:
        return "unknown"
    return "current" if recorded.value == configured_model else "stale"
