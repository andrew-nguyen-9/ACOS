"""FTS5 lexical retrieval leg (Phase 12.7).

Native SQLite FTS5 BM25 replaces the Python ``rank_bm25`` leg of hybrid
retrieval — faster, no in-Python corpus, runs in the DB next to the data.

The table is **app-maintained**, not external-content + triggers: the indexed
text is not a normal SQL column (it is pipeline-passed / ``Document.metadata_json``
JSON), so there is nothing for an ``AFTER INSERT`` trigger to fire on. The
``RAGIndexer`` is the single write chokepoint into the retrieval corpus, so it
mirrors every Chroma write here too (see ``backend/rag/indexer.py``).

``tenant_id`` is forward-compat with 12.14.
# ponytail: tenant_id nullable + UNINDEXED now; NOT NULL after the 12.14 migration.
"""
from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

# Single source of truth for the DDL — the alembic migration and the tests both
# create the table from this constant.
CREATE_FTS5_SQL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5("
    "content, doc_id UNINDEXED, doc_type UNINDEXED, tenant_id UNINDEXED, "
    "tokenize = 'porter unicode61')"
)

_WORD = re.compile(r"[a-z0-9]+")


def _match_query(query: str) -> str:
    """Turn raw user text into a safe FTS5 MATCH expression.

    FTS5 treats ``" * - : ( ) ^`` and bare words like NEAR/AND/OR as query
    operators, so raw input can raise ``fts5: syntax error``. We extract bare
    word tokens and OR together quoted phrases — neutralizes every operator and
    keeps the value bindable (it is still passed as a bound ``?`` parameter, so
    there is no SQL injection surface; this only prevents query-syntax errors).
    """
    tokens = _WORD.findall(query.lower())
    return " OR ".join(f'"{t}"' for t in tokens)


def ensure_fts5(session: Session) -> None:
    """Create the FTS5 table if absent. Used by tests and benches; production
    creates it via the alembic migration."""
    session.execute(text(CREATE_FTS5_SQL))


def fts5_available(session: Session) -> bool:
    """True when the underlying SQLite has the FTS5 module compiled in.

    AC §9: the shipped PyInstaller bundle must also pass this — the lexical leg
    is dead in production if ``CREATE VIRTUAL TABLE ... fts5`` raises there.
    """
    try:
        session.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)"))
        session.execute(text("DROP TABLE IF EXISTS _fts5_probe"))
        return True
    except Exception:
        return False


def upsert(session: Session, doc_id: str, content: str, doc_type: str, tenant_id: str | None = None) -> None:
    """Mirror one document into the FTS5 index. FTS5 has no native upsert, so
    delete-then-insert by ``doc_id`` keeps it idempotent."""
    session.execute(text("DELETE FROM documents_fts WHERE doc_id = :doc_id"), {"doc_id": doc_id})
    session.execute(
        text(
            "INSERT INTO documents_fts (content, doc_id, doc_type, tenant_id) "
            "VALUES (:content, :doc_id, :doc_type, :tenant_id)"
        ),
        {"content": content, "doc_id": doc_id, "doc_type": doc_type, "tenant_id": tenant_id},
    )


def delete(session: Session, doc_id: str) -> None:
    session.execute(text("DELETE FROM documents_fts WHERE doc_id = :doc_id"), {"doc_id": doc_id})


def search(session: Session, query: str, doc_types: list[str], k: int = 10) -> list[dict]:
    """FTS5 MATCH + bm25() rank, filtered to ``doc_types``.

    Returns ``[{"id", "text", "doc_type", "lexical_score"}]`` best-first. SQLite
    ``bm25()`` returns a value where *more negative = better*; we negate it to a
    positive score and normalize to ``[0, 1]`` so the reranker can fuse it with
    the dense semantic score.
    """
    match = _match_query(query)
    if not match or not doc_types:
        return []

    placeholders = ", ".join(f":dt{i}" for i in range(len(doc_types)))
    params: dict[str, object] = {"match": match, "k": k}
    params.update({f"dt{i}": dt for i, dt in enumerate(doc_types)})

    rows = session.execute(
        text(
            "SELECT doc_id, content, doc_type, bm25(documents_fts) AS score "
            "FROM documents_fts "
            f"WHERE documents_fts MATCH :match AND doc_type IN ({placeholders}) "
            "ORDER BY score LIMIT :k"
        ),
        params,
    ).all()
    if not rows:
        return []

    # bm25 is negative (best = most negative); negate so higher = better, then
    # normalize by the best score in this result set.
    raw = [-float(r.score) for r in rows]
    top = max(raw) or 1.0
    return [
        {
            "id": r.doc_id,
            "text": r.content,
            "doc_type": r.doc_type,
            "lexical_score": round(raw[i] / top, 6),
        }
        for i, r in enumerate(rows)
    ]
