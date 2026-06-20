from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.optimization import OptimizationProposal, OptimizationLog
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


class OptimizationLogRepository(BaseRepository[OptimizationLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(OptimizationLog, session)

    def list_for_proposal(self, proposal_id: str) -> list[OptimizationLog]:
        return list(
            self.session.scalars(
                select(OptimizationLog).where(OptimizationLog.proposal_id == proposal_id)
            ).all()
        )

    def list_recent(self, limit: int = 50) -> list[OptimizationLog]:
        return list(
            self.session.scalars(
                select(OptimizationLog)
                .order_by(OptimizationLog.created_at.desc())
                .limit(limit)
            ).all()
        )
