from __future__ import annotations

from sqlalchemy import String, Text, Float, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin


class Memory(TenantScopedMixin, Base):
    """Persistent context memory for the Phase 10 intelligence layer.

    Stores what worked across applications: long-term outcome signals, plus
    role-specific and company-specific patterns. Short-term (session) memory
    lives in-process and is never persisted here.
    """

    __tablename__ = "memory"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('short_term','long_term','role_specific','company_specific')",
            name="ck_memory_type",
        ),
        Index("idx_memory_role_type", "role_type"),
        Index("idx_memory_company", "company"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)
    role_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
