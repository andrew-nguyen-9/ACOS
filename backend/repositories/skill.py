from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.skill import Skill, SkillEvidence
from backend.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: Session) -> None:
        super().__init__(Skill, session)

    def get_by_name(self, name: str) -> Skill | None:
        return self.session.scalars(
            select(Skill).where(Skill.name == name)
        ).first()

    def get_by_category(self, category: str) -> list[Skill]:
        return list(
            self.session.scalars(
                select(Skill).where(Skill.category == category)
            ).all()
        )

    def get_or_create(self, name: str, category: str, proficiency: str = "intermediate") -> tuple[Skill, bool]:
        """Return (skill, created). created=True if new row was inserted."""
        existing = self.get_by_name(name)
        if existing:
            return existing, False
        skill = self.create(name=name, category=category, proficiency=proficiency)
        return skill, True

    def add_evidence(
        self,
        skill_id: str,
        source_type: str,
        source_id: str,
        evidence_text: str,
        confidence_level: str = "verified",
    ) -> SkillEvidence:
        ev = SkillEvidence(
            skill_id=skill_id,
            source_type=source_type,
            source_id=source_id,
            evidence_text=evidence_text,
            confidence_level=confidence_level,
        )
        self.session.add(ev)
        self.session.flush()
        self.session.refresh(ev)
        return ev
