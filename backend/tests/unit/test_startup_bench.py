"""Unit tests for the cold-start perf harness (scripts/perf/startup_bench.py).

Uses a trivial subprocess snippet so the harness logic (timing, stats, JSON
write) is verified without paying the cost of importing the real backend.
"""
import json

from scripts.perf import startup_bench

# Sleeps ~1ms so measured ms is reliably > 0 (no flaky zero-duration sample).
_FAST_SNIPPET = (
    "import time;_t=time.perf_counter();time.sleep(0.001);"
    'print(f"__PERF__{(time.perf_counter()-_t)*1000:.4f}")'
)


def test_run_returns_stats_and_writes_json(tmp_path):
    out = tmp_path / "startup.json"
    result = startup_bench.run(n=2, out_path=out, snippet=_FAST_SNIPPET)

    assert result["n"] == 2
    assert result["median_ms"] > 0
    assert result["p95_ms"] >= result["median_ms"]
    assert len(result["samples"]) == 2

    data = json.loads(out.read_text())
    assert data["median_ms"] == result["median_ms"]
    assert "machine" in data
    assert data["machine"]["python"]


def test_run_without_out_path_does_not_write(tmp_path):
    result = startup_bench.run(n=1, out_path=None, snippet=_FAST_SNIPPET)
    assert result["n"] == 1
    assert result["median_ms"] > 0
