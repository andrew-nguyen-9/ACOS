from __future__ import annotations

from sqlalchemy import String, Text, Boolean, CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, generate_uuid, utcnow


class Experience(TimestampMixin, Base):
    __tablename__ = "experiences"
    __table_args__ = (
        CheckConstraint(
            "employment_type IN ('full_time','part_time','contract','internship','freelance')",
            name="ck_experience_employment_type",
        ),
        CheckConstraint(
            "source IN ('manual','resume_import','linkedin','document_import')",
            name="ck_experience_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    bullets: Mapped[list[ExperienceBullet]] = relationship(
        "ExperienceBullet",
        back_populates="experience",
        cascade="all, delete-orphan",
        order_by="ExperienceBullet.order_index",
    )


class ExperienceBullet(Base):
    __tablename__ = "experience_bullets"
    __table_args__ = (
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_bullet_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    experience_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False
    )
    bullet_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified"
    )
    evidence_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    experience: Mapped[Experience] = relationship("Experience", back_populates="bullets")
