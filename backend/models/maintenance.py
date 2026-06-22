from __future__ import annotations

from sqlalchemy import String, Text, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow

# Action taxonomy a suggestion can wrap (bound to 11.1/11.2/11.3 services in the executor).
SUGGESTION_TYPES = ("reindex", "prompt_rollback", "model_switch", "embedding_refresh")
# A suggestion is inert until approved; only the executor moves it to executed/failed.
SUGGESTION_STATUSES = ("suggested", "approved", "executed", "dismissed", "failed")
AUDIT_EVENTS = ("suggested", "approved", "executed", "dismissed", "failed")


class MaintenanceSuggestion(Base):
    __tablename__ = "maintenance_suggestion"
    __table_args__ = (
        CheckConstraint(
            "type IN ('reindex','prompt_rollback','model_switch','embedding_refresh')",
            name="ck_maint_suggestion_type",
        ),
        CheckConstraint(
            "status IN ('suggested','approved','executed','dismissed','failed')",
            name="ck_maint_suggestion_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="suggested")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(32), default=utcnow, onupdate=utcnow)
    executed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class MaintenanceAudit(Base):
    __tablename__ = "maintenance_audit"
    __table_args__ = (
        CheckConstraint(
            "event IN ('suggested','approved','executed','dismissed','failed')",
            name="ck_maint_audit_event",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    suggestion_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("maintenance_suggestion.id", ondelete="SET NULL"),
        nullable=True,
    )
    event: Mapped[str] = mapped_column(String(20), nullable=False)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(40), nullable=False, default="user")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
