from __future__ import annotations

from sqlalchemy import String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class OptimizationProposal(Base):
    __tablename__ = "optimization_proposals"
    __table_args__ = (
        CheckConstraint(
            "target_engine IN ('resume','ats','rag','cover_letter','copilot')",
            name="ck_opt_proposal_engine",
        ),
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_opt_proposal_confidence",
        ),
        CheckConstraint(
            "risk_level IN ('low','medium','high')",
            name="ck_opt_proposal_risk",
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected','reverted')",
            name="ck_opt_proposal_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    target_engine: Mapped[str] = mapped_column(String(20), nullable=False)
    target_parameter: Mapped[str] = mapped_column(Text, nullable=False)
    current_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(32), default=utcnow, onupdate=utcnow)
    decided_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
