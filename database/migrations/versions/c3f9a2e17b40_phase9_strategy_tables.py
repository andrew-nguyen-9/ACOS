"""Phase 9 strategy tables: role_fit_cache, skill_gaps

Revision ID: c3f9a2e17b40
Revises: bd8b1c798504
Create Date: 2026-06-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3f9a2e17b40"
down_revision: Union[str, None] = "bd8b1c798504"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_fit_cache",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("jd_hash", sa.Text, nullable=False, unique=True),
        sa.Column("fit_score", sa.Float, nullable=False),
        sa.Column("skill_overlap", sa.Float, nullable=False),
        sa.Column("experience_alignment", sa.Float, nullable=False),
        sa.Column("industry_alignment", sa.Float, nullable=False),
        sa.Column("historical_similarity", sa.Float, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("missing_critical_skills", sa.Text, nullable=False, server_default="[]"),
        sa.Column(
            "confidence",
            sa.String(20),
            nullable=False,
            server_default="weak_inference",
        ),
        sa.Column(
            "computed_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.CheckConstraint(
            "confidence IN ('verified','strong_inference','weak_inference')",
            name="ck_rfc_confidence",
        ),
    )

    op.create_table(
        "skill_gaps",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("skill_name", sa.Text, nullable=False),
        sa.Column("gap_type", sa.String(10), nullable=False),
        sa.Column("frequency", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocking_interviews", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expected_lift_per_hour", sa.Float, nullable=True),
        sa.Column("priority_rank", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "computed_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.CheckConstraint(
            "gap_type IN ('missing','weak')",
            name="ck_sg_gap_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("skill_gaps")
    op.drop_table("role_fit_cache")
