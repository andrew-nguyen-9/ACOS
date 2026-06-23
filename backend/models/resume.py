from __future__ import annotations

from sqlalchemy import String, Text, Integer, Float, Boolean, CheckConstraint, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin
from backend.security.encryption import EncryptedJSON  # 16.2 (ADR-015)


class ResumeTemplate(Base):
    __tablename__ = "resume_templates"
    __table_args__ = (
        CheckConstraint(
            "layout_type IN ('single_column','two_column','hybrid')",
            name="ck_template_layout",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    target_industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    layout_type: Mapped[str] = mapped_column(String(20), nullable=False, default="single_column")
    template_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)


class WritingProfile(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "writing_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    tone_descriptors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    structure_patterns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    vocabulary_patterns: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sample_sentences: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_doc_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Resume(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    application_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("resume_templates.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[dict] = mapped_column(EncryptedJSON, nullable=False, default=dict)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_master: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
