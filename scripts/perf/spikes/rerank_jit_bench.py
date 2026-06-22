"""ADV micro-opt (b) (Phase 12.9) — Is the reranker a JIT candidate?

THROWAWAY research bench (not shipped). The brief proposes Numba/Jax JIT of "the
reranking distance matrix." Post-12.7 there IS no distance matrix in the reranker:
backend/rag/reranker.py rerank() is a pure-Python SCALAR fusion loop over the
already-retrieved candidate set (dense similarity is computed upstream in Chroma's
C++, the FTS5 leg in SQLite). This bench times the REAL rerank() over a realistic
candidate count to show it is microsecond-scale — i.e. there is no hot matrix to
JIT, and a Numba/Jax warmup (hundreds of ms first-call compile) would dwarf the
entire operation.

Pure-CPU → always runs. Fixed seed → reproducible.

    .venv/bin/python scripts/perf/spikes/rerank_jit_bench.py --candidates 200
"""
from __future__ import annotations

import argparse
import platform
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

_SEED = 1209


def make_candidates(m: int) -> list[dict]:
    rng = random.Random(_SEED)
    conf = ["verified", "strong_inference", "weak_inference"]
    return [{
        "id": f"c{i}",
        "semantic_score": rng.random(),
        "lexical_score": rng.random(),
        "metadata": {"confidence_level": rng.choice(conf),
                     "outcome_signal_weight": rng.random() * 3,
                     "entity_id": f"e{i}"},
    } for i in range(m)]


def run(m: int, iters: int) -> dict:
    from backend.rag.reranker import Reranker

    reranker = Reranker()
    cands = make_candidates(m)
    # warm the import/path once, then best-of-3 timing
    reranker.rerank("query text", cands)

    best = float("inf")
    for _ in range(3):
        t0 = time.perf_counter()
        for _ in range(iters):
            reranker.rerank("query text", cands)
        best = min(best, (time.perf_counter() - t0) / iters)
    per_call_us = best * 1e6
    return {
        "metric": "rerank_us",
        "candidates": m,
        "iters": iters,
        "per_call_us": round(per_call_us, 2),
        "note": "no distance matrix exists post-12.7; scalar fusion only",
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="rerank() microbench (JIT-candidacy check)")
    ap.add_argument("--candidates", type=int, default=200,
                    help="candidate set size (post-retrieval, pre-rerank)")
    ap.add_argument("--iters", type=int, default=5000)
    args = ap.parse_args()
    r = run(args.candidates, args.iters)
    print(f"rerank() over {r['candidates']} candidates: {r['per_call_us']}us/call "
          f"(scalar fusion, no matrix to JIT)")


if __name__ == "__main__":
    main()
