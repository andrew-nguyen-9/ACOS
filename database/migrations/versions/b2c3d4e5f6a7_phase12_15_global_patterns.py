"""Phase 12.15 privacy-preserving aggregation: global_patterns table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 19:00:00.000000

Content-free cross-tenant aggregate store (ADR-009): abstract fields + a tenant COUNT
only. No tenant_id, no raw text, no embeddings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "global_patterns",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("pattern_type", sa.String(40), nullable=False),
        sa.Column("industry", sa.String(40), nullable=False),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("metric", sa.String(40), nullable=False, server_default="interview_lift"),
        sa.Column("tenant_count", sa.Integer, nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="strong_inference"),
        sa.Column(
            "created_at", sa.String(32), nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
    )
    op.create_index("idx_global_patterns_lookup", "global_patterns", ["pattern_type", "industry"])


def downgrade() -> None:
    op.drop_index("idx_global_patterns_lookup", table_name="global_patterns")
    op.drop_table("global_patterns")
