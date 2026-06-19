from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.outcome import OutcomeSignal
from backend.repositories.base import BaseRepository


class OutcomeSignalRepository(BaseRepository[OutcomeSignal]):
    def __init__(self, session: Session) -> None:
        super().__init__(OutcomeSignal, session)

    def get_by_application(self, application_id: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.application_id == application_id)
            ).all()
        )

    def get_by_resume(self, resume_id: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.resume_id == resume_id)
            ).all()
        )

    def get_by_signal_type(self, signal_type: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.signal_type == signal_type)
            ).all()
        )
