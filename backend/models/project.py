from __future__ import annotations

from sqlalchemy import String, Text, Boolean, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, generate_uuid
from backend.models.tenant import TenantScopedMixin


class Project(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_project_confidence",
        ),
        CheckConstraint(
            "source IN ('manual','github','document_import','claude_export')",
            name="ck_project_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_ongoing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="verified"
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
