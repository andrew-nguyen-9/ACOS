"""Backend cold-start benchmark.

Measures `import backend.main` → `create_app()` ready time in a *fresh*
subprocess (so the import cache is cold every run), repeats N times, and
reports median / p95. Results are machine-tagged: compare deltas across runs
on the same machine, not absolute numbers across machines (see roadmap §10).

Usage:
    python scripts/perf/startup_bench.py            # N=5, writes baselines/startup.json
    python scripts/perf/startup_bench.py --n 10
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
from datetime import date
from math import ceil
from pathlib import Path

_MARKER = "__PERF__"

# Child times itself from before the import to after create_app() returns, then
# prints `__PERF__<ms>`. Run in a fresh interpreter so the import is always cold.
_DEFAULT_SNIPPET = (
    "import time;_t=time.perf_counter();"
    "import backend.main;backend.main.create_app();"
    f'print(f"{_MARKER}{{(time.perf_counter()-_t)*1000:.3f}}")'
)

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "startup.json"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _measure_once(snippet: str) -> float:
    """Run the snippet in a fresh interpreter, return the reported ms."""
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith(_MARKER):
            return float(line[len(_MARKER):])
    raise RuntimeError(f"no {_MARKER} line in child output:\n{proc.stdout}\n{proc.stderr}")


def _p95(samples: list[float]) -> float:
    """Nearest-rank p95. For tiny N this collapses toward the max."""
    ordered = sorted(samples)
    idx = ceil(0.95 * len(ordered)) - 1
    return ordered[max(idx, 0)]


def run(n: int = 5, out_path: Path | None = _DEFAULT_OUT, snippet: str = _DEFAULT_SNIPPET) -> dict:
    samples = [_measure_once(snippet) for _ in range(n)]
    result = {
        "metric": "backend_cold_start_ms",
        "date": date.today().isoformat(),
        "n": n,
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(_p95(samples), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "samples": [round(s, 3) for s in samples],
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend cold-start benchmark")
    parser.add_argument("--n", type=int, default=5, help="number of cold-start runs")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="JSON output path")
    args = parser.parse_args()
    result = run(n=args.n, out_path=args.out)
    print(
        f"cold start (n={result['n']}): "
        f"median={result['median_ms']}ms  p95={result['p95_ms']}ms  "
        f"min={result['min_ms']}ms  max={result['max_ms']}ms"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
