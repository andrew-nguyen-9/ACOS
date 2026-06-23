"""Phase 16.1 (ADR-014): auth credentials + sessions

Adds the two tables that bind a request to a tenant via an authenticated session,
replacing the unauthenticated X-Tenant-Id selector (ADR-008). Neither stores a
secret: auth_credentials holds a scrypt verifier, auth_sessions a token digest.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-06-23 18:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_credentials",
        sa.Column("tenant_id", sa.String(32), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("salt", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=True),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(32), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=True),
        sa.Column("expires_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_auth_sessions_tenant_id", "auth_sessions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_tenant_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("auth_credentials")
