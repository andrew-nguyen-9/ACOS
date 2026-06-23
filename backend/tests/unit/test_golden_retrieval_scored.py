"""Phase 13.10 (8b) — scored golden-set retrieval harness.

12.7's golden harness asserted FTS5 was *equal-or-better* than BM25 per query. This
adds a SCORED baseline — recall@k and MRR over the same fixed query→gold set — so
"retrieval correctness" is a measured number future changes regress against, not a
pass/fail filter. Lexical path only (FTS5/BM25), so it needs no live Ollama.

The baseline is frozen to baselines/retrieval_scored.json. Regenerate intentionally:

    python backend/tests/unit/test_golden_retrieval_scored.py
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.services.rag import lexical
from backend.tests.unit.test_fts5_golden import CORPUS, QUERIES, _DOC_TYPE

_BASELINE = Path(__file__).parent / "baselines" / "retrieval_scored.json"
_K = 3


def _ranked_ids(query: str) -> list[str]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session = sessionmaker(bind=engine)()
    try:
        lexical.ensure_fts5(session)
        for doc_id, text in CORPUS:
            lexical.upsert(session, doc_id, text, _DOC_TYPE)
        session.commit()
        return [r["id"] for r in lexical.search(session, query, [_DOC_TYPE], k=len(CORPUS))]
    finally:
        session.close()
        engine.dispose()


def _score() -> dict:
    """recall@k (gold in top-k) and MRR (1/rank of gold) over the query set."""
    hits, rr = 0, 0.0
    for query, gold_id in QUERIES:
        ids = _ranked_ids(query)
        rank = ids.index(gold_id) if gold_id in ids else None
        if rank is not None and rank < _K:
            hits += 1
        if rank is not None:
            rr += 1.0 / (rank + 1)
    n = len(QUERIES)
    return {"recall_at_k": round(hits / n, 4), "mrr": round(rr / n, 4), "k": _K, "n": n}


def test_scored_retrieval_meets_frozen_baseline():
    assert _BASELINE.is_file(), (
        "scored baseline missing — freeze it: python backend/tests/unit/test_golden_retrieval_scored.py"
    )
    baseline = json.loads(_BASELINE.read_text())
    current = _score()
    # A regression is a measured drop below the frozen number (float-safe epsilon).
    assert current["recall_at_k"] >= baseline["recall_at_k"] - 1e-9, (
        f"recall@{_K} regressed: {current['recall_at_k']} < {baseline['recall_at_k']}"
    )
    assert current["mrr"] >= baseline["mrr"] - 1e-9, (
        f"MRR regressed: {current['mrr']} < {baseline['mrr']}"
    )


def _freeze() -> None:
    scores = _score()
    _BASELINE.parent.mkdir(parents=True, exist_ok=True)
    _BASELINE.write_text(
        json.dumps({"source": "FTS5 lexical, frozen Phase 13.10", **scores}, indent=2) + "\n"
    )
    print(f"wrote {_BASELINE} :: {scores}")


if __name__ == "__main__":
    _freeze()
