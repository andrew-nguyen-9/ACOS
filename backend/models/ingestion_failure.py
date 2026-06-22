from __future__ import annotations

from sqlalchemy import String, Text, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class IngestionFailure(Base):
    """Dead-letter record for a file that failed ingestion after retries.

    Distinct from ``ingestion_logs`` (per-stage audit of a *persisted* document):
    a failure may never produce a Document row, so this stands alone by path.
    """

    __tablename__ = "ingestion_failures"
    __table_args__ = (
        CheckConstraint(
            "error_type IN ('transient','permanent')",
            name="ck_ingestion_failure_error_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    error_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
