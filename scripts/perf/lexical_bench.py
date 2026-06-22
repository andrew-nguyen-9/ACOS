"""Lexical-retrieval latency benchmark (Phase 12.7).

Times the FTS5 lexical leg (``lexical.search``) over a synthetic corpus and, when
``rank_bm25`` is still importable, the equivalent Python BM25 build+score so the
swap can be compared head-to-head.

FTS5 is pure SQLite — no Ollama — so unlike the other perf benches this one runs
unconditionally (no ``OLLAMA_LIVE`` gate):

    python scripts/perf/lexical_bench.py
    python scripts/perf/lexical_bench.py --docs 2000 --queries 200

Uses a throwaway in-memory SQLite DB — never touches the real database.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "lexical.json"

# Synthetic career-domain vocabulary — each doc is a random-ish sentence so FTS5
# and BM25 have a realistic term distribution to rank over.
_VOCAB = (
    "python react sql kubernetes docker pipeline data machine learning model "
    "async event loop performance throughput latency api service frontend "
    "backend database query index orchestration deployment training inference "
    "embedding vector retrieval ranking optimization migration schema design "
    "typescript fastapi gradient batch warehouse etl container concurrency"
).split()


def _make_corpus(n: int, seed: int = 1234) -> list[tuple[str, str]]:
    import random

    rng = random.Random(seed)
    corpus = []
    for i in range(n):
        words = rng.sample(_VOCAB, k=rng.randint(8, 16))
        corpus.append((f"d{i}", " ".join(words)))
    return corpus


def _make_queries(corpus: list[tuple[str, str]], n: int, seed: int = 99) -> list[str]:
    import random

    rng = random.Random(seed)
    # Queries are 3-5 word slices of real docs so they actually match.
    queries = []
    for _ in range(n):
        _, text = rng.choice(corpus)
        toks = text.split()
        k = min(len(toks), rng.randint(3, 5))
        queries.append(" ".join(rng.sample(toks, k=k)))
    return queries


def _bench_fts5(corpus, queries, doc_type) -> list[float]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from backend.services.rag import lexical

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session = sessionmaker(bind=engine)()
    try:
        lexical.ensure_fts5(session)
        for doc_id, text in corpus:
            lexical.upsert(session, doc_id, text, doc_type)
        session.commit()
        samples = []
        for q in queries:
            t0 = time.perf_counter()
            lexical.search(session, q, [doc_type], k=10)
            samples.append((time.perf_counter() - t0) * 1000.0)
        return samples
    finally:
        session.close()
        engine.dispose()


def _bench_python_bm25(corpus, queries) -> list[float] | None:
    """Per-query cost of the OLD path: build BM25Okapi over the corpus + score.

    The old reranker rebuilt BM25 per call over the candidate set, so building +
    scoring is the fair per-query comparison. Returns None if rank_bm25 is gone.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None

    tokenized = [text.lower().split() for _, text in corpus]
    samples = []
    for q in queries:
        t0 = time.perf_counter()
        bm25 = BM25Okapi(tokenized)
        bm25.get_scores(q.lower().split())
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def _stats(samples: list[float]) -> dict:
    s = sorted(samples)
    return {
        "median_ms": round(statistics.median(s), 4),
        "p95_ms": round(s[min(len(s) - 1, int(len(s) * 0.95))], 4),
        "min_ms": round(min(s), 4),
        "max_ms": round(max(s), 4),
    }


def run(docs: int = 1000, queries: int = 100, out_path: Path | None = _DEFAULT_OUT) -> dict:
    corpus = _make_corpus(docs)
    qs = _make_queries(corpus, queries)
    doc_type = "acos_experiences"

    fts = _stats(_bench_fts5(corpus, qs, doc_type))
    py = _bench_python_bm25(corpus, qs)
    result = {
        "metric": "lexical_query_ms",
        "date": date.today().isoformat(),
        "docs": docs,
        "queries": queries,
        "fts5": fts,
        "python_bm25": _stats(py) if py else "rank_bm25 not installed (removed in 12.7)",
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "sqlite": _sqlite_version(),
        },
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def _sqlite_version() -> str:
    import sqlite3

    return sqlite3.sqlite_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Lexical (FTS5 vs Python BM25) latency benchmark")
    parser.add_argument("--docs", type=int, default=1000)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = parser.parse_args()

    result = run(docs=args.docs, queries=args.queries, out_path=args.out)
    fts = result["fts5"]
    print(f"FTS5 ({result['docs']} docs, {result['queries']} q): "
          f"median={fts['median_ms']}ms  p95={fts['p95_ms']}ms")
    if isinstance(result["python_bm25"], dict):
        py = result["python_bm25"]
        print(f"Python BM25 (build+score/q):     median={py['median_ms']}ms  p95={py['p95_ms']}ms")
        print(f"speedup (median): {round(py['median_ms'] / fts['median_ms'], 1)}x")
    else:
        print(result["python_bm25"])
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
