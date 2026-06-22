"""Phase 11.1 fault tolerance: ingestion_failures dead-letter table

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e2b3c4d5f6a7"
down_revision: Union[str, None] = "d1a2b3c4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_failures",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("error_type", sa.String(20), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.CheckConstraint(
            "error_type IN ('transient','permanent')",
            name="ck_ingestion_failure_error_type",
        ),
    )
    op.create_index(
        "idx_ingestion_failures_created_at", "ingestion_failures", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "idx_ingestion_failures_created_at", table_name="ingestion_failures"
    )
    op.drop_table("ingestion_failures")
