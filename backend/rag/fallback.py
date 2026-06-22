"""Keyword fallback retrieval over SQLite (Phase 11.1).

A safety net for when ChromaDB is unavailable or empty: a term-overlap search
over experience bullet text already in SQLite. Not a second ranking engine —
just "good enough to keep working", flagged ``degraded`` upstream so the UI can
set expectations.

# ponytail: LIKE scan over bullets; swap to SQLite FTS5 only if the corpus
# grows past a few thousand rows (it won't for a single-user career OS).
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from backend.models.experience import ExperienceBullet

_WORD = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class KeywordFallback:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        terms = set(_terms(query))
        if not terms:
            return []

        scored: list[tuple[float, ExperienceBullet]] = []
        for bullet in self._session.query(ExperienceBullet).all():
            bullet_terms = set(_terms(bullet.bullet_text))
            if not bullet_terms:
                continue
            matched = terms & bullet_terms
            if not matched:
                continue
            scored.append((len(matched) / len(terms), bullet))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {
                "text": bullet.bullet_text[:300],
                "source": "acos_experiences",
                "entity_id": bullet.id,
                "confidence": bullet.confidence_level,
                "similarity_score": round(score, 4),
            }
            for score, bullet in scored[:top_k]
        ]
