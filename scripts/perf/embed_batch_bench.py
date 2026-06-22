"""Embedding-batch throughput benchmark against live Ollama (Phase 12.6 AC3).

Compares the old per-chunk path (one POST /api/embeddings per text) against the
batched path (one POST /api/embed per <=128-chunk). Reports wall time AND the
HTTP-call count for each — the round-trip reduction is the win.

    OLLAMA_LIVE=1 python scripts/perf/embed_batch_bench.py --n 300

With OLLAMA_LIVE unset it prints "skipped" and exits 0.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "embed_batch.json"


def _live() -> bool:
    return bool(os.environ.get("OLLAMA_LIVE"))


def run(n: int = 300, out_path: Path | None = _DEFAULT_OUT) -> dict | None:
    from backend.config import get_settings
    from backend.rag.embedder import Embedder
    from backend.services.ollama_client import OllamaClient

    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    if not ollama.is_available():
        print(f"skipped: Ollama not reachable at {settings.ollama_base_url}")
        return None

    model = settings.embedding_model
    texts = [f"Engineer led project {i} improving latency and reliability." for i in range(n)]

    # Per-chunk path: one HTTP call per text.
    seq_calls = 0
    t0 = time.perf_counter()
    for t in texts:
        ollama.embed(model=model, text=t)
        seq_calls += 1
    seq_s = time.perf_counter() - t0

    # Batched path: count the actual POST /api/embed calls.
    embedder = Embedder(ollama, model=model)
    batch_calls = 0
    real_embed_batch = ollama.embed_batch

    def _counting_embed_batch(model: str, texts: list[str]):  # type: ignore[no-redef]
        nonlocal batch_calls
        batch_calls += 1
        return real_embed_batch(model=model, texts=texts)

    ollama.embed_batch = _counting_embed_batch  # type: ignore[method-assign]
    t0 = time.perf_counter()
    embedder.embed_batch(texts)
    batch_s = time.perf_counter() - t0
    ollama.embed_batch = real_embed_batch  # type: ignore[method-assign]

    result = {
        "metric": "embed_batch",
        "date": date.today().isoformat(),
        "n": n,
        "sequential": {"http_calls": seq_calls, "seconds": round(seq_s, 3)},
        "batched": {"http_calls": batch_calls, "seconds": round(batch_s, 3)},
        "speedup_x": round(seq_s / batch_s, 2) if batch_s else None,
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    if not _live():
        print("skipped: set OLLAMA_LIVE=1 to run the live embed-batch bench")
        return
    parser = argparse.ArgumentParser(description="Embedding batch throughput benchmark")
    parser.add_argument("--n", type=int, default=300, help="number of texts to embed")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="JSON output path")
    args = parser.parse_args()

    result = run(n=args.n, out_path=args.out)
    if result is None:
        return
    s, b = result["sequential"], result["batched"]
    print(
        f"embed (n={result['n']}): "
        f"sequential={s['http_calls']} calls {s['seconds']}s  |  "
        f"batched={b['http_calls']} calls {b['seconds']}s  |  "
        f"speedup={result['speedup_x']}x"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
