from __future__ import annotations

from sqlalchemy import String, Text, CheckConstraint, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin


# Many-to-many association tables
experience_skills_table = Table(
    "experience_skills",
    Base.metadata,
    Column("experience_id", String(32), ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", String(32), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

project_skills_table = Table(
    "project_skills",
    Base.metadata,
    Column("project_id", String(32), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", String(32), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


class Skill(TenantScopedMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "category IN ('programming','data','domain','soft','tool','methodology')",
            name="ck_skill_category",
        ),
        CheckConstraint(
            "proficiency IN ('exposure','beginner','intermediate','advanced','expert')",
            name="ck_skill_proficiency",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    proficiency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="intermediate"
    )
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(32), default=utcnow, onupdate=utcnow)

    evidence: Mapped[list[SkillEvidence]] = relationship(
        "SkillEvidence",
        back_populates="skill",
        cascade="all, delete-orphan",
    )


class SkillEvidence(Base):
    __tablename__ = "skill_evidence"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('experience','project','github','document','self_reported')",
            name="ck_evidence_source_type",
        ),
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_evidence_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    skill_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified"
    )
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    skill: Mapped[Skill] = relationship("Skill", back_populates="evidence")
