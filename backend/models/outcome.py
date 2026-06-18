from __future__ import annotations

from sqlalchemy import String, Text, Float, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class OutcomeSignal(Base):
    __tablename__ = "outcome_signals"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('no_response','rejected','phone_screen','interview','final_round','offer','accepted')",
            name="ck_outcome_signal_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_weight: Mapped[float] = mapped_column(Float, nullable=False)
    template_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
