"""Phase 12.14 tenant isolation: tenants table + tenant_id on owned tables

Revision ID: a1b2c3d4e5f6
Revises: c4d5e6f7a8b9
Create Date: 2026-06-22 18:00:00.000000

One revision, nullable -> backfill -> NOT NULL + FK (ADR-008). Existing single-user
rows are re-homed losslessly into the ``default`` tenant. SQLite needs
``batch_alter_table`` (table rebuild) to add a NOT NULL column + FK.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TENANT_ID = "default"

# Owned tables that gain a NEW tenant_id column.
_NEW_COLUMN_TABLES = [
    "experiences", "projects", "skills", "applications", "resumes",
    "writing_profiles", "questions", "answers", "documents", "generation_logs",
    "knowledge_graph_nodes", "knowledge_graph_edges", "outcome_signals",
    "metrics", "memory",
]
# signals already has a nullable tenant_id (12.10) — constrain it, don't re-add.


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.Text, nullable=False, server_default="default"),
        sa.Column(
            "created_at", sa.String(32), nullable=False,
            server_default=sa.text("(datetime('now'))"),
        ),
    )
    op.execute(
        sa.text("INSERT INTO tenants (id, name) VALUES (:id, :name)").bindparams(
            id=DEFAULT_TENANT_ID, name="default"
        )
    )

    for table in _NEW_COLUMN_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("tenant_id", sa.String(32), nullable=True))
        op.execute(f"UPDATE {table} SET tenant_id = '{DEFAULT_TENANT_ID}'")
        with op.batch_alter_table(table) as batch:
            batch.alter_column("tenant_id", existing_type=sa.String(32), nullable=False)
            batch.create_foreign_key(
                f"fk_{table}_tenant", "tenants", ["tenant_id"], ["id"]
            )
            batch.create_index(f"ix_{table}_tenant_id", ["tenant_id"])

    # signals: column exists (nullable). Backfill + constrain + FK. Swap the 12.10
    # index name to the mixin's create_all name so fresh and migrated DBs match.
    op.execute(f"UPDATE signals SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    op.drop_index("idx_signals_tenant", table_name="signals")
    with op.batch_alter_table("signals") as batch:
        batch.alter_column("tenant_id", existing_type=sa.String(32), nullable=False)
        batch.create_foreign_key("fk_signals_tenant", "tenants", ["tenant_id"], ["id"])
        batch.create_index("ix_signals_tenant_id", ["tenant_id"])


def downgrade() -> None:
    # signals keeps its (now nullable again) tenant_id column — it predates this revision.
    with op.batch_alter_table("signals") as batch:
        batch.drop_index("ix_signals_tenant_id")
        batch.drop_constraint("fk_signals_tenant", type_="foreignkey")
        batch.alter_column("tenant_id", existing_type=sa.String(32), nullable=True)
    op.create_index("idx_signals_tenant", "signals", ["tenant_id"])  # restore 12.10 index

    for table in _NEW_COLUMN_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_tenant_id")
            batch.drop_constraint(f"fk_{table}_tenant", type_="foreignkey")
            batch.drop_column("tenant_id")

    op.drop_table("tenants")
