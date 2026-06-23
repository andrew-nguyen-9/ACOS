"""Phase 13.10 (8a) — live-Ollama bench gate.

One runnable command that re-runs the TTFT + structured-output benches against a live
Ollama and prints a combined summary to paste into docs/PERFORMANCE_LOG.md.

    OLLAMA_LIVE=1 python scripts/perf/live_bench_runner.py
    OLLAMA_LIVE=1 python scripts/perf/live_bench_runner.py --n 10

With OLLAMA_LIVE unset it prints "skipped" and exits 0 — this environment has no live
Ollama, so the numbers below are produced only on a machine that does (the segment-time
numbers in PERFORMANCE_LOG stand until then). ponytail: thin orchestration over the
existing ttft_bench.run / structured_output_bench.run — no new bench logic.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root

from scripts.perf import structured_output_bench, ttft_bench  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=None, help="samples per bench (bench defaults apply if unset)")
    args = parser.parse_args()

    if not os.environ.get("OLLAMA_LIVE"):
        print("skipped: set OLLAMA_LIVE=1 (and have Ollama running) to record live numbers")
        sys.exit(0)

    results: dict[str, object] = {}
    results["ttft"] = ttft_bench.run(**({"n": args.n} if args.n else {}))
    results["structured_output"] = structured_output_bench.run(**({"n": args.n} if args.n else {}))

    print("\n=== Phase 13.10 live-bench summary (paste into PERFORMANCE_LOG.md) ===")
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
