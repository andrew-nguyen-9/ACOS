from __future__ import annotations

from sqlalchemy import select, delete, or_
from sqlalchemy.orm import Session

from backend.models.base import utcnow
from backend.models.memory import Memory
from backend.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, session: Session) -> None:
        super().__init__(Memory, session)

    def retrieve(
        self,
        role_type: str | None = None,
        company: str | None = None,
    ) -> list[Memory]:
        """Return non-expired memories matching role_type OR company, highest confidence first.

        With no filters, returns an empty list (memory injection requires a target).
        """
        if role_type is None and company is None:
            return []

        now = utcnow()
        filters = []
        if role_type is not None:
            filters.append(Memory.role_type == role_type)
        if company is not None:
            filters.append(Memory.company == company)

        stmt = (
            select(Memory)
            .where(or_(*filters))
            .where(or_(Memory.expires_at.is_(None), Memory.expires_at > now))
            .order_by(Memory.confidence.desc())
        )
        return list(self.session.scalars(stmt).all())

    def prune_expired(self) -> int:
        """Delete all memories whose expires_at is in the past. Returns count removed."""
        now = utcnow()
        result = self.session.execute(
            delete(Memory).where(Memory.expires_at.is_not(None), Memory.expires_at < now)
        )
        self.session.flush()
        return result.rowcount
