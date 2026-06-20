from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.optimization import OptimizationProposal
from backend.repositories.base import BaseRepository


class OptimizationProposalRepository(BaseRepository[OptimizationProposal]):
    def __init__(self, session: Session) -> None:
        super().__init__(OptimizationProposal, session)

    def list_by_status(self, status: str) -> list[OptimizationProposal]:
        return list(
            self.session.scalars(
                select(OptimizationProposal).where(OptimizationProposal.status == status)
            ).all()
        )
