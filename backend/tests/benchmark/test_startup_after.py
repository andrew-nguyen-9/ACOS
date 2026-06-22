"""Startup regression guard (Phase 11.3).

The 11.3 startup win comes from keeping chromadb (and its heavy transitive deps:
numpy, onnxruntime, opentelemetry, grpc) off the import path until first use.
This guard asserts that **deterministically**: chromadb must not be in
`sys.modules` after `create_app()`. It catches a heavy import sneaking back onto
the startup path regardless of machine speed.

Wall-clock budget (median/p95 ≤ baseline + 10%) is *not* asserted here — cold
start runs hundreds of ms and a coverage-instrumented suite on a busy machine
inflates it 2–3x, which would make a hard gate flaky. The strict budget is
measured out-of-band with `scripts/perf/startup_bench.py` and recorded in
`docs/PERFORMANCE_LOG.md` (same convention as 11.1/11.2).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_chromadb_not_imported_at_startup():
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys, backend.main; backend.main.create_app();"
         "sys.exit(0 if 'chromadb' not in sys.modules else 1)"],
        cwd=_REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, "chromadb was imported at startup (lazy-init regressed)"
