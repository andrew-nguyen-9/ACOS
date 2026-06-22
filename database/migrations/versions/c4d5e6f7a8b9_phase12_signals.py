"""Phase 12.10 feedback-loop: signals table

Revision ID: c4d5e6f7a8b9
Revises: b5c6d7e8f9a0
Create Date: 2026-06-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.String(32), primary_key=True),
        # tenant_id nullable until 12.14 (tenant isolation backfills + constrains).
        sa.Column("tenant_id", sa.String(32), nullable=True),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("signal_type", sa.String(40), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default=sa.text("1.0")),
        sa.Column("source_json", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.String(32),
            nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
    )
    op.create_index("idx_signals_tenant", "signals", ["tenant_id"])
    op.create_index("idx_signals_entity", "signals", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("idx_signals_entity", table_name="signals")
    op.drop_index("idx_signals_tenant", table_name="signals")
    op.drop_table("signals")
