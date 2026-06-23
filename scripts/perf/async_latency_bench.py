"""Concurrency latency — sync (blocking Session + threads) vs async (aiosqlite + gather).

Phase 12.2 before/after on one machine in one run. Both modes hit the *same*
temp-file WAL database and run the *same* read workload; the only difference is
the stack 12.2 swapped: a blocking ``Session`` driven by N OS threads vs an
``AsyncSession`` over aiosqlite driven by ``asyncio.gather`` on the (uvloop)
event loop. This isolates the engine change, not the route plumbing.

    python scripts/perf/async_latency_bench.py --requests 80 --concurrency 8

ponytail: a read-scan workload — the contended case the async swap targets
(SQLite has a single writer regardless, so writes can't parallelize anyway).
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from math import ceil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.database import _apply_pragmas, _to_async_url

_ROWS = 2000
_SCANS_PER_REQUEST = 30  # extend each request's I/O so concurrency overlap is visible
_QUERY = "SELECT COUNT(*), MAX(n) FROM bench WHERE n > 0"


def _percentile(samples: list[float], pct: float) -> float:
    ordered = sorted(samples)
    return ordered[max(ceil(pct * len(ordered)) - 1, 0)]


def _summarize(latencies: list[float], wall_s: float, n: int, concurrency: int) -> dict:
    return {
        "n_requests": n,
        "concurrency": concurrency,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
        "throughput_rps": round(n / wall_s, 1) if wall_s > 0 else 0.0,
    }


def _seed(db_path: str) -> None:
    eng = create_engine(f"sqlite:///{db_path}")
    event.listen(eng, "connect", _apply_pragmas)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE bench (id INTEGER PRIMARY KEY, n INTEGER)"))
        c.execute(
            text("INSERT INTO bench (n) VALUES " + ",".join(f"({i})" for i in range(1, _ROWS + 1)))
        )
    eng.dispose()


def run_sync(db_path: str, n_requests: int, concurrency: int) -> dict:
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    event.listen(eng, "connect", _apply_pragmas)

    def _one() -> float:
        t0 = time.perf_counter()
        with eng.connect() as c:
            for _ in range(_SCANS_PER_REQUEST):
                c.execute(text(_QUERY)).all()
        return (time.perf_counter() - t0) * 1000

    wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        latencies = list(pool.map(lambda _: _one(), range(n_requests)))
    wall_s = time.perf_counter() - wall0
    eng.dispose()
    return _summarize(latencies, wall_s, n_requests, concurrency)


async def run_async(db_path: str, n_requests: int, concurrency: int) -> dict:
    eng = create_async_engine(
        _to_async_url(f"sqlite:///{db_path}"), connect_args={"check_same_thread": False}
    )
    event.listen(eng.sync_engine, "connect", _apply_pragmas)
    sem = asyncio.Semaphore(concurrency)

    async def _one() -> float:
        async with sem:
            t0 = time.perf_counter()
            async with eng.connect() as c:
                for _ in range(_SCANS_PER_REQUEST):
                    (await c.execute(text(_QUERY))).all()
            return (time.perf_counter() - t0) * 1000

    wall0 = time.perf_counter()
    latencies = list(await asyncio.gather(*[_one() for _ in range(n_requests)]))
    wall_s = time.perf_counter() - wall0
    await eng.dispose()
    return _summarize(latencies, wall_s, n_requests, concurrency)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=80)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    # uvloop, as installed at the real server entry point (server_entry.install_uvloop).
    import uvloop

    uvloop.install()

    with TemporaryDirectory() as d:
        db_path = str(Path(d) / "bench.db")
        _seed(db_path)
        sync = run_sync(db_path, args.requests, args.concurrency)
        # fresh DB so the async run isn't reading the sync run's warm page cache
        db_path2 = str(Path(d) / "bench2.db")
        _seed(db_path2)
        asyncv = asyncio.run(run_async(db_path2, args.requests, args.concurrency))

    print(f"sync  (threads+Session):     {sync}")
    print(f"async (gather+AsyncSession): {asyncv}")


if __name__ == "__main__":
    main()
