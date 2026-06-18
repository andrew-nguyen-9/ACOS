from __future__ import annotations

from sqlalchemy import String, Text, Integer, Boolean, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class GenerationLog(Base):
    __tablename__ = "generation_logs"
    __table_args__ = (
        CheckConstraint(
            "generation_type IN ('resume','cover_letter','answer','copilot','ats_analysis')",
            name="ck_gen_log_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    generation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    application_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    prompt_name: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
