"""Phase 11.2 observability: metrics table

Revision ID: f3c4d5e6a7b8
Revises: e2b3c4d5f6a7
Create Date: 2026-06-21 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f3c4d5e6a7b8"
down_revision: Union[str, None] = "e2b3c4d5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("meta_json", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.CheckConstraint(
            "kind IN ('retrieval_quality','ats_score','interview_conversion',"
            "'embedding_drift','prompt_perf')",
            name="ck_metric_kind",
        ),
    )
    op.create_index("idx_metrics_kind_created", "metrics", ["kind", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_metrics_kind_created", table_name="metrics")
    op.drop_table("metrics")
