"""Phase 14.2: widen ck_metric_kind to allow 'success_rate'

Adds the resume-success-rate drift metric kind. SQLite can't ALTER a CHECK in
place, so batch_alter_table rebuilds the (append-only) metrics table with the
widened constraint.

Revision ID: c5d6e7f8a9b0
Revises: b2c3d4e5f6a7
Create Date: 2026-06-23 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = (
    "kind IN ('retrieval_quality','ats_score','interview_conversion',"
    "'embedding_drift','prompt_perf')"
)
_NEW = (
    "kind IN ('retrieval_quality','ats_score','interview_conversion',"
    "'embedding_drift','prompt_perf','success_rate')"
)


def upgrade() -> None:
    with op.batch_alter_table("metrics") as batch:
        batch.drop_constraint("ck_metric_kind", type_="check")
        batch.create_check_constraint("ck_metric_kind", _NEW)


def downgrade() -> None:
    with op.batch_alter_table("metrics") as batch:
        batch.drop_constraint("ck_metric_kind", type_="check")
        batch.create_check_constraint("ck_metric_kind", _OLD)
