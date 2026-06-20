from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.optimization import OptimizationProposal, OptimizationLog, PromptVersion, ABExperiment, ABVariant
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


class PromptVersionRepository(BaseRepository[PromptVersion]):
    def __init__(self, session: Session) -> None:
        super().__init__(PromptVersion, session)

    def get_active(self, prompt_name: str) -> PromptVersion | None:
        return self.session.scalars(
            select(PromptVersion).where(
                PromptVersion.prompt_name == prompt_name,
                PromptVersion.is_active.is_(True),
            )
        ).first()

    def list_for_prompt(self, prompt_name: str) -> list[PromptVersion]:
        return list(
            self.session.scalars(
                select(PromptVersion)
                .where(PromptVersion.prompt_name == prompt_name)
                .order_by(PromptVersion.created_at.asc())
            ).all()
        )

    def activate(self, version_id: str) -> PromptVersion:
        target = self.get(version_id)
        if target is None:
            raise ValueError(f"PromptVersion {version_id} not found")
        # Deactivate all siblings, then activate the target (single-active invariant).
        for sibling in self.list_for_prompt(target.prompt_name):
            sibling.is_active = sibling.id == version_id
        self.session.flush()
        return target


class ABExperimentRepository(BaseRepository[ABExperiment]):
    def __init__(self, session: Session) -> None:
        super().__init__(ABExperiment, session)

    def list_running(self) -> list[ABExperiment]:
        return list(
            self.session.scalars(
                select(ABExperiment).where(ABExperiment.status == "running")
            ).all()
        )


class ABVariantRepository(BaseRepository[ABVariant]):
    def __init__(self, session: Session) -> None:
        super().__init__(ABVariant, session)

    def list_for_experiment(self, experiment_id: str) -> list[ABVariant]:
        return list(
            self.session.scalars(
                select(ABVariant).where(ABVariant.experiment_id == experiment_id)
            ).all()
        )
