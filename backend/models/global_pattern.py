"""Phase 12.15 content-free cross-tenant aggregate store (ADR-009).

A `global_patterns` row holds ONLY abstract fields: a pattern type, an industry key,
an abstract label (e.g. a skill name — shared vocabulary, not user content), an
aggregate numeric value, the contributing-tenant **count** (never ids), and a
confidence level. No `tenant_id` (it is cross-tenant by definition, so NOT a
TenantScopedMixin table), no raw text, no embeddings.
"""
from __future__ import annotations

from sqlalchemy import String, Float, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class GlobalPattern(Base):
    __tablename__ = "global_patterns"
    __table_args__ = (
        Index("idx_global_patterns_lookup", "pattern_type", "industry"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    pattern_type: Mapped[str] = mapped_column(String(40), nullable=False)
    industry: Mapped[str] = mapped_column(String(40), nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)        # abstract label (skill, section)
    value: Mapped[float] = mapped_column(Float, nullable=False)   # aggregate numeric (e.g. mean ROI)
    metric: Mapped[str] = mapped_column(String(40), nullable=False, default="interview_lift")
    tenant_count: Mapped[int] = mapped_column(Integer, nullable=False)  # count, never ids
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="strong_inference")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
