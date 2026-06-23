"""Request-latency harness under concurrency — sync baseline for Phase 12.2.

Phase 12.2 swaps the sync stack (blocking SQLAlchemy + default asyncio loop)
for uvloop + aiosqlite + async sessions. To prove that change helps, we need a
*before* number now: p50/p95 latency of a request path under N concurrent
callers against the current synchronous app.

`run_latency_bench` is the reusable slot 12.2 re-runs after the async swap to
compute the delta. It is intentionally framework-light (stdlib threads +
percentiles) so it measures the server, not a load tool.

    pytest backend/tests/benchmark/test_async_latency.py -q
"""
from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from typing import Callable

# ponytail: nearest-rank percentile, same convention as scripts/perf/startup_bench.py.
# A numpy/interpolating percentile is not worth a dep for a dev-run latency bench.
def _percentile(samples: list[float], pct: float) -> float:
    ordered = sorted(samples)
    idx = ceil(pct * len(ordered)) - 1
    return ordered[max(idx, 0)]


def run_latency_bench(
    call: Callable[[], object],
    n_requests: int = 40,
    concurrency: int = 8,
) -> dict:
    """Fire `n_requests` through `call` with `concurrency` workers; report latency.

    `call` is any zero-arg callable that performs one request and returns
    something truthy on success (e.g. a TestClient response). Latency is wall
    time per call in milliseconds. Returns p50/p95/min/max plus throughput.
    """
    latencies: list[float] = []

    def _timed() -> float:
        t0 = time.perf_counter()
        call()
        return (time.perf_counter() - t0) * 1000

    wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        latencies = list(pool.map(lambda _: _timed(), range(n_requests)))
    wall_s = time.perf_counter() - wall0

    return {
        "n_requests": n_requests,
        "concurrency": concurrency,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "throughput_rps": round(n_requests / wall_s, 1) if wall_s > 0 else 0.0,
    }


def test_run_latency_bench_reports_percentiles(client):
    """Harness runs against the live (sync) /health path and returns p50/p95."""
    def _call():
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        return resp

    result = run_latency_bench(_call, n_requests=24, concurrency=4)

    # The contract 12.2 depends on: real percentile numbers come back.
    assert result["n_requests"] == 24
    assert result["p50_ms"] > 0
    assert result["p95_ms"] >= result["p50_ms"]
    assert result["max_ms"] >= result["p95_ms"]
    assert result["throughput_rps"] > 0


def test_percentile_nearest_rank():
    samples = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert _percentile(samples, 0.5) == 30.0
    assert _percentile(samples, 0.95) == 100.0
