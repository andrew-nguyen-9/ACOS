"""Phase 10 intelligence layer: memory table

Revision ID: d1a2b3c4e5f6
Revises: c3f9a2e17b40
Create Date: 2026-06-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1a2b3c4e5f6"
down_revision: Union[str, None] = "c3f9a2e17b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("memory_type", sa.String(20), nullable=False),
        sa.Column("role_type", sa.String(40), nullable=True),
        sa.Column("company", sa.Text, nullable=True),
        sa.Column("content_json", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
        sa.Column("expires_at", sa.String(32), nullable=True),
        sa.CheckConstraint(
            "memory_type IN ('short_term','long_term','role_specific','company_specific')",
            name="ck_memory_type",
        ),
    )
    op.create_index("idx_memory_role_type", "memory", ["role_type"])
    op.create_index("idx_memory_company", "memory", ["company"])


def downgrade() -> None:
    op.drop_index("idx_memory_company", table_name="memory")
    op.drop_index("idx_memory_role_type", table_name="memory")
    op.drop_table("memory")
