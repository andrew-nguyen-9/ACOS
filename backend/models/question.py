from __future__ import annotations

from sqlalchemy import String, Text, CheckConstraint, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, generate_uuid, utcnow


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('behavioral','technical','situational','motivational','cultural','role_specific')",
            name="ck_question_category",
        ),
        CheckConstraint(
            "length_target IN ('short','medium','long')",
            name="ck_question_length",
        ),
        CheckConstraint(
            "source IN ('manual','job_description','generated','import')",
            name="ck_question_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    question_template: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="behavioral")
    length_target: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    variables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    answers: Mapped[list[Answer]] = relationship(
        "Answer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_answer_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    question_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    original_answer: Mapped[str] = mapped_column(Text, nullable=False)
    edited_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified"
    )
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(32), default=utcnow, onupdate=utcnow)

    question: Mapped[Question] = relationship("Question", back_populates="answers")
