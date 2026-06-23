from __future__ import annotations

from sqlalchemy import String, Float, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class Signal(Base):
    """Phase 12.10 feedback-loop signal — the flywheel's normalized event.

    One row per derived outcome signal (ATS score, interview result, skill used)
    that the 12.11 ROI engine and 12.13 prompt evolution consume. Every signal
    links back to the source record(s) it was derived from via ``source_json``
    (Trap 1 / CLAUDE.md confidence system) — a signal with no traceable source is
    a bug, so the engine refuses to write one.

    No CHECK on entity_type/signal_type: the signal vocabulary grows with each
    flywheel segment; the engine validates, the schema stays open.
    """

    __tablename__ = "signals"
    __table_args__ = (
        Index("idx_signals_tenant", "tenant_id"),
        Index("idx_signals_entity", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    # tenant_id nullable until 12.14 (tenant isolation backfills + constrains it).
    tenant_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # source_json: {"table": <source table>, "ids": [<source record ids>]} — the
    # explainability anchor explain() reads back. No FK: sources span many tables.
    source_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)  # the signal ts
