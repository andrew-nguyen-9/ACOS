"""Spike 1 (Phase 12.9) — IPC serialization microbench: JSON vs msgpack.

THROWAWAY research bench (not shipped, not imported by the app). Measures the
serialize+deserialize cost of a ~50k-char "generated document" payload — the
kind that crosses the Tauri<->backend HTTP boundary (lib.rs spawns the FastAPI
sidecar; transport is HTTP-JSON). This is a MICROBENCH of codec cost only, NOT a
new transport — spec §3 non-goal.

Pure-CPU → always runs (no OLLAMA_LIVE gate). Fixed seed → reproducible table.

    .venv/bin/python scripts/perf/spikes/ipc_msgpack_bench.py --n 2000

Ad-hoc dep (documented in findings, NOT added to requirements):
    .venv/bin/python -m pip install "msgpack>=1.0"
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import time

import msgpack  # ad-hoc bench dep; not in backend/requirements.txt

_SEED = 1209


def build_payload(target_chars: int = 50_000) -> dict:
    """Deterministic ~50k-char payload shaped like a generated-document response:
    one long prose body + metadata + a list of evidence chunks."""
    rng = random.Random(_SEED)
    words = ["led", "shipped", "reduced", "latency", "pipeline", "resume", "ATS",
             "evidence", "confidence", "verified", "inference", "retrieval",
             "embedding", "tenant", "throughput", "Ollama", "Chroma", "FastAPI"]

    def sentence(n: int) -> str:
        return " ".join(rng.choice(words) for _ in range(n)).capitalize() + "."

    body_parts: list[str] = []
    chunks: list[dict] = []
    chars = 0
    i = 0
    while chars < target_chars:
        s = sentence(rng.randint(12, 30))
        body_parts.append(s)
        chunks.append({
            "id": f"chunk-{i}",
            "doc_type": rng.choice(["resume", "job_description", "profile"]),
            "semantic_score": round(rng.random(), 6),
            "lexical_score": round(rng.random(), 6),
            "confidence_level": rng.choice(["verified", "strong_inference", "weak_inference"]),
            "text": s,
        })
        chars += len(s)
        i += 1

    return {
        "document": " ".join(body_parts),
        "metadata": {"tone": "professional", "model": "qwen3:8b", "tokens": chars // 4},
        "evidence": chunks,
    }


def _time(fn, iters: int) -> float:
    """Return microseconds per call (best-of-3 medianish: take the min of 3 runs)."""
    best = float("inf")
    for _ in range(3):
        t0 = time.perf_counter()
        for _ in range(iters):
            fn()
        best = min(best, (time.perf_counter() - t0) / iters)
    return best * 1e6  # us


def run(n: int) -> dict:
    payload = build_payload()
    char_count = len(payload["document"]) + sum(len(c["text"]) for c in payload["evidence"])

    json_bytes = json.dumps(payload).encode()
    mp_bytes = msgpack.packb(payload)

    # Reproducibility self-check: both codecs must round-trip identically.
    assert json.loads(json_bytes.decode()) == payload
    assert msgpack.unpackb(mp_bytes, raw=False) == payload

    json_ser = _time(lambda: json.dumps(payload).encode(), n)
    json_de = _time(lambda: json.loads(json_bytes.decode()), n)
    mp_ser = _time(lambda: msgpack.packb(payload), n)
    mp_de = _time(lambda: msgpack.unpackb(mp_bytes, raw=False), n)

    json_rt = json_ser + json_de
    mp_rt = mp_ser + mp_de
    return {
        "metric": "ipc_codec_us",
        "n": n,
        "payload_chars": char_count,
        "json": {"bytes": len(json_bytes), "ser_us": round(json_ser, 2),
                 "de_us": round(json_de, 2), "rt_us": round(json_rt, 2)},
        "msgpack": {"bytes": len(mp_bytes), "ser_us": round(mp_ser, 2),
                    "de_us": round(mp_de, 2), "rt_us": round(mp_rt, 2)},
        "msgpack_rt_speedup_x": round(json_rt / mp_rt, 2) if mp_rt else None,
        "rt_saved_us": round(json_rt - mp_rt, 2),
        "msgpack_version": ".".join(map(str, msgpack.version)),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="JSON vs msgpack codec microbench")
    ap.add_argument("--n", type=int, default=2000, help="iterations per timed codec op")
    args = ap.parse_args()
    r = run(args.n)
    j, m = r["json"], r["msgpack"]
    print(f"payload: {r['payload_chars']} chars  (json {j['bytes']}B / msgpack {m['bytes']}B)")
    print(f"JSON    ser {j['ser_us']:8.2f}us  de {j['de_us']:8.2f}us  rt {j['rt_us']:8.2f}us")
    print(f"msgpack ser {m['ser_us']:8.2f}us  de {m['de_us']:8.2f}us  rt {m['rt_us']:8.2f}us")
    print(f"round-trip speedup: {r['msgpack_rt_speedup_x']}x  (saves {r['rt_saved_us']}us/req)")


if __name__ == "__main__":
    main()
