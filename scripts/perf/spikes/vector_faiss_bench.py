"""Spike 2 (Phase 12.9) — Vector store: Chroma vs FAISS (float) vs FAISS binary-quant.

THROWAWAY research bench (not shipped, not imported by the app; faiss-cpu is NOT
in backend/requirements.txt). Compares the production-default store (Chroma, which
12.6 consolidated to ONE physical collection partitioned by doc_type metadata)
against two FAISS challengers over a FIXED corpus:

  - Chroma IndexFlat (cosine)        — production reference, ranks define recall ref
  - FAISS  IndexFlatIP (float exact) — exact NN; also the ground truth for binary
  - FAISS  IndexBinaryFlat (Hamming) — binary-quantized (768 bits -> 96 bytes/vec,
                                       32x smaller); TRADES recall for memory

Reports recall@k (overlap), per-query latency, and index memory for each. A
latency/memory win that tanks recall is a reject (spec trap 3).

Default corpus = SEEDED synthetic unit vectors → always runs, reproducible.
OLLAMA_LIVE=1 → embed a fixed set of seeded sentences via the real nomic-embed-text
path (embed_batch, reused from 12.6) for realistic embedding geometry.

    .venv/bin/python scripts/perf/spikes/vector_faiss_bench.py --n 2000 --q 50 --k 15
    OLLAMA_LIVE=1 .venv/bin/python scripts/perf/spikes/vector_faiss_bench.py --n 1000

Ad-hoc dep (documented in findings, NOT added to requirements):
    .venv/bin/python -m pip install faiss-cpu
"""
from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from pathlib import Path

import faiss  # ad-hoc bench dep; not in backend/requirements.txt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

_SEED = 1209
_DIM = 768  # nomic-embed-text


def _live() -> bool:
    return bool(os.environ.get("OLLAMA_LIVE"))


def _normalize(x: np.ndarray) -> np.ndarray:
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-12)


def build_corpus(n: int, q: int) -> tuple[np.ndarray, np.ndarray, str]:
    """Return (corpus[n,dim], queries[q,dim], source). Unit-normalized float32."""
    if _live():
        from backend.config import get_settings
        from backend.services.ollama_client import OllamaClient

        settings = get_settings()
        ollama = OllamaClient(base_url=settings.ollama_base_url)
        if ollama.is_available():
            rng = np.random.default_rng(_SEED)
            verbs = ["led", "shipped", "reduced", "scaled", "designed", "migrated"]
            nouns = ["pipeline", "latency", "resume parser", "retrieval layer",
                     "tenant isolation", "embedding cache", "ATS scorer"]
            texts = [f"{verbs[i % len(verbs)]} the {nouns[(i * 7) % len(nouns)]} "
                     f"improving metric {i}" for i in range(n + q)]
            vecs = np.asarray(ollama.embed_batch(model=settings.embedding_model, texts=texts),
                              dtype=np.float32)
            vecs = _normalize(vecs)
            return vecs[:n], vecs[n:n + q], f"live:{settings.embedding_model}"
        print("OLLAMA_LIVE set but Ollama unreachable — falling back to synthetic")

    rng = np.random.default_rng(_SEED)
    allv = _normalize(rng.standard_normal((n + q, _DIM)).astype(np.float32))
    return allv[:n], allv[n:n + q], "synthetic"


def _topk_ids(D_or_neg, I) -> list[set[int]]:
    return [set(row.tolist()) for row in I]


def _recall(got: list[set[int]], ref: list[set[int]], k: int) -> float:
    return float(np.mean([len(g & r) / k for g, r in zip(got, ref)]))


def _pack_binary(vecs: np.ndarray, thresh: np.ndarray) -> np.ndarray:
    """Sign-quantize each dim vs per-dim threshold, bitpack to uint8 (d/8 bytes)."""
    bits = (vecs > thresh).astype(np.uint8)
    return np.packbits(bits, axis=1)


def run(n: int, q: int, k: int) -> dict:
    corpus, queries, source = build_corpus(n, q)

    # --- Chroma (production reference) ---
    import chromadb

    client = chromadb.EphemeralClient()
    coll = client.create_collection("spike", metadata={"hnsw:space": "cosine"})
    ids = [str(i) for i in range(n)]
    t0 = time.perf_counter()
    coll.add(ids=ids, embeddings=corpus.tolist())
    chroma_build = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    cres = coll.query(query_embeddings=queries.tolist(), n_results=k)
    chroma_query = (time.perf_counter() - t0) * 1e3 / q
    chroma_ref = [set(int(x) for x in row) for row in cres["ids"]]

    # --- FAISS float (exact inner-product == cosine on unit vectors) ---
    t0 = time.perf_counter()
    fidx = faiss.IndexFlatIP(_DIM)
    fidx.add(corpus)
    faiss_build = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    _, fI = fidx.search(queries, k)
    faiss_query = (time.perf_counter() - t0) * 1e3 / q
    faiss_ref = _topk_ids(_, fI)  # exact NN = ground truth for binary

    # --- FAISS binary-quant (Hamming) ---
    thresh = corpus.mean(axis=0, keepdims=True)  # sign-after-centering
    cb = _pack_binary(corpus, thresh)
    qb = _pack_binary(queries, thresh)
    t0 = time.perf_counter()
    bidx = faiss.IndexBinaryFlat(_DIM)
    bidx.add(cb)
    bin_build = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter()
    _, bI = bidx.search(qb, k)
    bin_query = (time.perf_counter() - t0) * 1e3 / q
    bin_got = _topk_ids(_, bI)

    float_mb = n * _DIM * 4 / 1e6
    bin_mb = n * (_DIM // 8) / 1e6
    return {
        "metric": "vector_store_spike",
        "source": source,
        "n": n, "q": q, "k": k, "dim": _DIM,
        "chroma": {"build_ms": round(chroma_build, 2), "query_ms": round(chroma_query, 3),
                   "recall_vs_self": 1.0, "mem_mb": round(float_mb, 2)},
        "faiss_float": {"build_ms": round(faiss_build, 2), "query_ms": round(faiss_query, 3),
                        "recall_vs_chroma": round(_recall(faiss_ref, chroma_ref, k), 4),
                        "mem_mb": round(float_mb, 2)},
        "faiss_binary": {"build_ms": round(bin_build, 2), "query_ms": round(bin_query, 3),
                         "recall_vs_exact": round(_recall(bin_got, faiss_ref, k), 4),
                         "recall_vs_chroma": round(_recall(bin_got, chroma_ref, k), 4),
                         "mem_mb": round(bin_mb, 3), "mem_reduction_x": round(float_mb / bin_mb, 1)},
        "faiss_version": faiss.__version__,
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Chroma vs FAISS vector-store spike")
    ap.add_argument("--n", type=int, default=2000, help="corpus vectors")
    ap.add_argument("--q", type=int, default=50, help="queries")
    ap.add_argument("--k", type=int, default=15, help="top-k")
    args = ap.parse_args()
    r = run(args.n, args.q, args.k)
    print(f"corpus={r['n']} dim={r['dim']} k={r['k']} source={r['source']}")
    c, f, b = r["chroma"], r["faiss_float"], r["faiss_binary"]
    print(f"chroma        build {c['build_ms']:7.1f}ms  query {c['query_ms']:.3f}ms  "
          f"recall 1.000 (ref)  mem {c['mem_mb']:.2f}MB")
    print(f"faiss_float   build {f['build_ms']:7.1f}ms  query {f['query_ms']:.3f}ms  "
          f"recall {f['recall_vs_chroma']:.3f} vs chroma  mem {f['mem_mb']:.2f}MB")
    print(f"faiss_binary  build {b['build_ms']:7.1f}ms  query {b['query_ms']:.3f}ms  "
          f"recall {b['recall_vs_exact']:.3f} vs exact / {b['recall_vs_chroma']:.3f} vs chroma  "
          f"mem {b['mem_mb']:.3f}MB ({b['mem_reduction_x']}x smaller)")


if __name__ == "__main__":
    main()
