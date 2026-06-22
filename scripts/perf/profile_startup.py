"""Profile backend cold start to find import-time hotspots.

cProfiles a fresh `import backend.main` + `create_app()` and prints the top
functions by cumulative time. Use this to decide *what* to make lazy; pair with
startup_bench.py to measure whether a change actually moved the median.

Usage:
    python scripts/perf/profile_startup.py            # top 25 by cumtime
    python scripts/perf/profile_startup.py --top 40
    python scripts/perf/profile_startup.py --importtime   # per-module import cost
"""
from __future__ import annotations

import argparse
import cProfile
import pstats
import subprocess
import sys
from io import StringIO
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def profile_cprofile(top: int) -> str:
    """cProfile a cold create_app() in-process and return the top-N report."""
    pr = cProfile.Profile()
    pr.enable()
    import backend.main  # noqa: PLC0415 — intentional: measure the import

    backend.main.create_app()
    pr.disable()

    buf = StringIO()
    pstats.Stats(pr, stream=buf).sort_stats("cumulative").print_stats(top)
    return buf.getvalue()


def profile_importtime() -> str:
    """Aggregate `python -X importtime` self-time by top-level module (fresh proc)."""
    proc = subprocess.run(
        [sys.executable, "-X", "importtime", "-c",
         "import backend.main; backend.main.create_app()"],
        capture_output=True, text=True, cwd=_REPO_ROOT,
    )
    agg: dict[str, int] = {}
    for line in proc.stderr.splitlines():
        # format: "import time:  <self> | <cumulative> | <module>"
        parts = line.split("|")
        if len(parts) != 3 or "import time:" not in parts[0]:
            continue
        try:
            self_us = int(parts[0].split(":")[1].strip())
        except ValueError:
            continue
        top = parts[2].strip().split(".")[0]
        agg[top] = agg.get(top, 0) + self_us
    lines = [f"{us / 1000:8.1f} ms  {name}"
             for name, us in sorted(agg.items(), key=lambda x: -x[1])[:20]]
    return "Per top-level module self import-time:\n" + "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile backend cold start")
    parser.add_argument("--top", type=int, default=25, help="rows to print (cProfile)")
    parser.add_argument("--importtime", action="store_true",
                        help="aggregate per-module import cost instead of cProfile")
    args = parser.parse_args()
    print(profile_importtime() if args.importtime else profile_cprofile(args.top))


if __name__ == "__main__":
    main()
