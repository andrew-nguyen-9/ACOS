"""Golden comparison: FTS5 lexical ranking is equal-or-better than Python BM25.

Phase 12.7 AC §4: "results equal-or-better vs the Python BM25 baseline
(documented comparison)." No golden-set harness existed in-repo, so this file
*is* the harness.

The baseline (rank position of each query's gold doc under ``rank_bm25``) was
captured while the Python dependency was still present and frozen to
``baselines/lexical_golden.json`` — see the ``__main__`` capture block. The test
reads that frozen JSON (it does NOT import rank_bm25, so it keeps passing after
the dependency is removed) and asserts FTS5 ranks each gold doc at an equal or
better (lower) position.

Regenerate the baseline (only meaningful while rank_bm25 is installed):

    python backend/tests/unit/test_fts5_golden.py
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.rag import lexical

_BASELINE = Path(__file__).parent / "baselines" / "lexical_golden.json"

# Fixed corpus — career-domain docs, one doc_type so the golden focuses on
# ranking (doc_type filtering is covered in test_fts5_lexical.py).
_DOC_TYPE = "acos_experiences"
CORPUS: list[tuple[str, str]] = [
    ("py_async", "Optimized a Python asyncio event loop for high-throughput request performance"),
    ("py_web", "Built a Python web service with FastAPI handling concurrent requests"),
    ("react_ui", "Designed a React frontend component library and design system in TypeScript"),
    ("vue_ui", "Created a Vue frontend dashboard with reusable component widgets"),
    ("sql_tune", "Tuned slow SQL database queries with composite indexes and query plans"),
    ("nosql", "Modeled document data in a NoSQL database for flexible schema storage"),
    ("ml_train", "Trained a machine learning model with gradient descent and cross validation"),
    ("ml_serve", "Served machine learning inference behind a low latency prediction API"),
    ("k8s", "Deployed containerized services to Kubernetes with rolling orchestration"),
    ("docker", "Packaged applications into Docker containers for reproducible builds"),
    ("pipeline", "Engineered a data pipeline for batch processing and high throughput ingestion"),
    ("etl", "Built ETL jobs extracting and transforming records into a data warehouse"),
]
# (query, gold doc_id that should rank best lexically)
QUERIES: list[tuple[str, str]] = [
    ("python asyncio event loop performance", "py_async"),
    ("react frontend component design system", "react_ui"),
    ("sql database query tuning indexes", "sql_tune"),
    ("machine learning model training", "ml_train"),
    ("kubernetes container orchestration deployment", "k8s"),
    ("data pipeline batch processing throughput", "pipeline"),
]


def _fts_rank(gold_id: str, query: str) -> int:
    """Position (0-indexed) of ``gold_id`` in the FTS5 ranking, or a large
    sentinel if it does not appear."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    try:
        lexical.ensure_fts5(session)
        for doc_id, text in CORPUS:
            lexical.upsert(session, doc_id, text, _DOC_TYPE)
        session.commit()
        ids = [r["id"] for r in lexical.search(session, query, [_DOC_TYPE], k=len(CORPUS))]
        return ids.index(gold_id) if gold_id in ids else len(CORPUS)
    finally:
        session.close()
        engine.dispose()


def test_fts5_equal_or_better_than_python_bm25():
    assert _BASELINE.is_file(), (
        "golden baseline missing — capture it with rank_bm25 installed: "
        "python backend/tests/unit/test_fts5_golden.py"
    )
    baseline = json.loads(_BASELINE.read_text())["ranks"]

    regressions = []
    for query, gold_id in QUERIES:
        fts = _fts_rank(gold_id, query)
        base = baseline[gold_id]
        # equal-or-better == FTS5 rank position is <= the Python BM25 position.
        if fts > base:
            regressions.append(f"{gold_id!r}: FTS5 rank {fts} worse than BM25 {base}")
    assert not regressions, "FTS5 ranked gold docs worse than the Python BM25 baseline:\n" + "\n".join(
        regressions
    )


def test_fts5_ranks_gold_doc_first():
    """Sanity: each query's gold doc is the top FTS5 hit."""
    for query, gold_id in QUERIES:
        assert _fts_rank(gold_id, query) == 0, f"{gold_id!r} not top hit for {query!r}"


def _capture_baseline() -> None:
    """Record rank_bm25's rank position for each gold doc; freeze to JSON.

    Imported lazily so the test module loads without rank_bm25 (post-removal).
    """
    from rank_bm25 import BM25Okapi  # noqa: PLC0415

    tokenized = [text.lower().split() for _, text in CORPUS]
    bm25 = BM25Okapi(tokenized)
    ids = [doc_id for doc_id, _ in CORPUS]
    ranks: dict[str, int] = {}
    for query, gold_id in QUERIES:
        scores = bm25.get_scores(query.lower().split())
        order = [ids[i] for i in sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)]
        ranks[gold_id] = order.index(gold_id)
    _BASELINE.parent.mkdir(parents=True, exist_ok=True)
    _BASELINE.write_text(
        json.dumps(
            {
                "source": "rank_bm25==0.2.2 (BM25Okapi), frozen Phase 12.7",
                "corpus_size": len(CORPUS),
                "ranks": ranks,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {_BASELINE} :: {ranks}")


if __name__ == "__main__":
    _capture_baseline()
