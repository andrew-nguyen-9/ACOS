"""Phase 12.7 FTS5: lexical search virtual table

Revision ID: b5c6d7e8f9a0
Revises: a4d5e6f7b8c9
Create Date: 2026-06-22 12:00:00.000000

Adds the ``documents_fts`` FTS5 virtual table for native BM25 lexical retrieval
(replaces the Python rank_bm25 leg). It is **app-maintained** by ``RAGIndexer``
(no triggers — the indexed text is not a normal SQL column), so this migration
only creates/drops the table. ``op.create_table`` cannot express a virtual
table, and the env's ``render_as_batch`` (SQLite ALTER) does not apply to raw
DDL, so we use ``op.execute`` with the DDL constant shared with the runtime.
"""
from typing import Sequence, Union

from alembic import op

from backend.services.rag.lexical import CREATE_FTS5_SQL

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a4d5e6f7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(CREATE_FTS5_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS documents_fts")
