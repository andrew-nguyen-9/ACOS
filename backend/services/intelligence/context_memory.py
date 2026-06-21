from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.repositories.memory import MemoryRepository

logger = logging.getLogger(__name__)


class ContextMemory:
    """Persist and retrieve cross-session context for the intelligence layer.

    Backed by SQLite exact-match retrieval on role_type / company.
    # ponytail: exact-match retrieval; add ChromaDB semantic memory only if
    # cross-role pattern transfer is measurably needed.
    """

    def __init__(self, session: Session) -> None:
        self._repo = MemoryRepository(session)

    def record(
        self,
        memory_type: str,
        content: dict,
        role_type: str | None = None,
        company: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Persist a memory. content is JSON-serialized for storage."""
        self._repo.create(
            memory_type=memory_type,
            role_type=role_type,
            company=company,
            content_json=json.dumps(content),
            confidence=confidence,
        )

    def record_outcome(
        self,
        role_type: str | None,
        company: str | None,
        content: dict,
        confidence: float = 1.0,
    ) -> None:
        """Persist a long-term outcome signal (which bullets led to which result)."""
        self.record(
            memory_type="long_term",
            content=content,
            role_type=role_type,
            company=company,
            confidence=confidence,
        )

    def retrieve(
        self,
        role_type: str | None = None,
        company: str | None = None,
    ) -> list[dict]:
        """Return parsed memory contents matching role_type OR company, best confidence first."""
        out: list[dict] = []
        for mem in self._repo.retrieve(role_type=role_type, company=company):
            try:
                out.append(json.loads(mem.content_json))
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("context_memory: skipping malformed memory %s: %s", mem.id, exc)
        return out

    def format_for_injection(
        self,
        role_type: str | None = None,
        company: str | None = None,
    ) -> str:
        """Render retrieved memories as `[MEMORY: ...]` lines for prompt prepending.

        Returns an empty string when no memories match.
        """
        memories = self.retrieve(role_type=role_type, company=company)
        if not memories:
            return ""
        lines = [f"[MEMORY: {m.get('insight') or json.dumps(m)}]" for m in memories]
        return "\n".join(lines)
