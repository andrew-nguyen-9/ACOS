"""Phase 11.4 maintenance: suggestion + audit tables

Revision ID: a4d5e6f7b8c9
Revises: f3c4d5e6a7b8
Create Date: 2026-06-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a4d5e6f7b8c9"
down_revision: Union[str, None] = "f3c4d5e6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_suggestion",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("payload_json", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="suggested"),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("snapshot_id", sa.String(120), nullable=True),
        sa.Column("created_at", sa.String(32), nullable=False,
                  server_default=sa.text("(datetime('now'))")),
        sa.Column("updated_at", sa.String(32), nullable=False,
                  server_default=sa.text("(datetime('now'))")),
        sa.Column("executed_at", sa.String(32), nullable=True),
        sa.CheckConstraint(
            "type IN ('reindex','prompt_rollback','model_switch','embedding_refresh')",
            name="ck_maint_suggestion_type",
        ),
        sa.CheckConstraint(
            "status IN ('suggested','approved','executed','dismissed','failed')",
            name="ck_maint_suggestion_status",
        ),
    )
    op.create_table(
        "maintenance_audit",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("suggestion_id", sa.String(32),
                  sa.ForeignKey("maintenance_suggestion.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("detail_json", sa.Text, nullable=True),
        sa.Column("actor", sa.String(40), nullable=False, server_default="user"),
        sa.Column("created_at", sa.String(32), nullable=False,
                  server_default=sa.text("(datetime('now'))")),
        sa.CheckConstraint(
            "event IN ('suggested','approved','executed','dismissed','failed')",
            name="ck_maint_audit_event",
        ),
    )
    op.create_index("idx_maint_audit_suggestion", "maintenance_audit", ["suggestion_id"])


def downgrade() -> None:
    op.drop_index("idx_maint_audit_suggestion", table_name="maintenance_audit")
    op.drop_table("maintenance_audit")
    op.drop_table("maintenance_suggestion")
