from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.experience import Experience, ExperienceBullet
from backend.repositories.base import BaseRepository


class ExperienceRepository(BaseRepository[Experience]):
    def __init__(self, session: Session) -> None:
        super().__init__(Experience, session)

    def get_by_company(self, company: str) -> list[Experience]:
        return list(
            self.session.scalars(
                select(Experience).where(Experience.company == company)
            ).all()
        )

    def get_current(self) -> list[Experience]:
        return list(
            self.session.scalars(
                select(Experience).where(Experience.is_current.is_(True))
            ).all()
        )

    def add_bullet(
        self,
        experience_id: str,
        bullet_text: str,
        confidence_level: str = "verified",
        order_index: int = 0,
        evidence_ids: str = "[]",
    ) -> ExperienceBullet:
        bullet = ExperienceBullet(
            experience_id=experience_id,
            bullet_text=bullet_text,
            confidence_level=confidence_level,
            order_index=order_index,
            evidence_ids=evidence_ids,
        )
        self.session.add(bullet)
        self.session.flush()
        self.session.refresh(bullet)
        return bullet
