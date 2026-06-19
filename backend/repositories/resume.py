from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.resume import Resume, ResumeTemplate, WritingProfile
from backend.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: Session) -> None:
        super().__init__(Resume, session)

    def get_by_application(self, application_id: str) -> list[Resume]:
        stmt = select(Resume).where(Resume.application_id == application_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_master(self) -> Resume | None:
        stmt = select(Resume).where(Resume.is_master == True)  # noqa: E712
        return self.session.execute(stmt).scalar_one_or_none()


class ResumeTemplateRepository(BaseRepository[ResumeTemplate]):
    def __init__(self, session: Session) -> None:
        super().__init__(ResumeTemplate, session)

    def get_default(self) -> ResumeTemplate | None:
        stmt = select(ResumeTemplate).where(ResumeTemplate.is_default == True)  # noqa: E712
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_industry(self, industry: str) -> ResumeTemplate | None:
        stmt = select(ResumeTemplate).where(ResumeTemplate.target_industry == industry)
        return self.session.execute(stmt).scalar_one_or_none()


class WritingProfileRepository(BaseRepository[WritingProfile]):
    def __init__(self, session: Session) -> None:
        super().__init__(WritingProfile, session)

    def get_latest(self) -> WritingProfile | None:
        stmt = select(WritingProfile).order_by(WritingProfile.updated_at.desc()).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()
