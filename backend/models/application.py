from __future__ import annotations

from sqlalchemy import String, Text, Integer, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin
from backend.security.encryption import EncryptedText


class Application(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','applied','phone_screen','interview','final_round','offer','rejected','withdrawn')",
            name="ck_application_status",
        ),
        CheckConstraint(
            "work_arrangement IS NULL OR work_arrangement IN ('remote','hybrid','onsite')",
            name="ck_application_work_arrangement",
        ),
        CheckConstraint(
            "source IS NULL OR source IN ('linkedin','indeed','referral','direct','recruiter','other')",
            name="ck_application_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 16.2 (ADR-015): sensitive free-text — opt-in encrypted at rest.
    job_description: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    job_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    date_applied: Mapped[str | None] = mapped_column(String(10), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    work_arrangement: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recruiter_name: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    recruiter_email: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    # 14.3/16.2: free-text PII — opt-in encrypted at rest (EncryptedText is a Text
    # passthrough when the flag is off, so the column/schema is unchanged).
    notes: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    timeline: Mapped[list[ApplicationTimeline]] = relationship(
        "ApplicationTimeline",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationTimeline.event_date",
    )


class ApplicationTimeline(Base):
    __tablename__ = "application_timeline"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('status_change','note_added','document_attached','interview_scheduled','outcome_recorded')",
            name="ck_timeline_event_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)  # 16.2
    event_date: Mapped[str] = mapped_column(String(32), nullable=False, default=utcnow)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    application: Mapped[Application] = relationship(
        "Application", back_populates="timeline"
    )
