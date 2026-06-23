from __future__ import annotations

from sqlalchemy import String, Float, JSON, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin


class Metric(TenantScopedMixin, Base):
    """Append-only observability metric sample (Phase 11.2).

    One row per recorded measurement; drift is computed by comparing rolling
    windows of these over time. Never updated — purely additive.
    """

    __tablename__ = "metrics"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('retrieval_quality','ats_score','interview_conversion',"
            "'embedding_drift','prompt_perf')",
            name="ck_metric_kind",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    meta_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
