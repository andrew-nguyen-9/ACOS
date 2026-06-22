"""Time-to-first-token (TTFT) benchmark against live Ollama.

Fires one warm-up `generate` (loads the model into memory) then N measured
calls, timing each end-to-end. Reports median / p95 in ms.

NOTE: `OllamaClient.generate` is non-streaming today (`stream: False`), so this
measures *time-to-full-response*, not true TTFT. Phase 12.4 adds the streaming
path; once it lands this bench switches to timing the first streamed chunk and
the number becomes true TTFT. Until then it is a stable upper-bound proxy on the
same path — good enough to track the 12.5 calibration delta.

This bench needs a running Ollama with the default model pulled. It is opt-in:

    OLLAMA_LIVE=1 python scripts/perf/ttft_bench.py            # N=5
    OLLAMA_LIVE=1 python scripts/perf/ttft_bench.py --n 10

With OLLAMA_LIVE unset it prints "skipped" and exits 0 (so CI without Ollama
stays green).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
from datetime import date
from math import ceil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import get_settings  # noqa: E402
from backend.services.ollama_client import OllamaClient  # noqa: E402

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "ttft.json"
_PROMPT = "List three strong action verbs for a software engineering resume."


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = ceil(0.95 * len(ordered)) - 1
    return ordered[max(idx, 0)]


def _live() -> bool:
    # ponytail: skip if OLLAMA_LIVE unset — no live-Ollama CI by design (roadmap §3).
    return bool(os.environ.get("OLLAMA_LIVE"))


def run(n: int = 5, out_path: Path | None = _DEFAULT_OUT) -> dict | None:
    import time

    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url)
    if not client.is_available():
        print(f"skipped: Ollama not reachable at {settings.ollama_base_url}")
        return None

    model = settings.default_model
    # Warm-up: load the model into memory so the measured runs are warm TTFT.
    client.generate(model=model, prompt=_PROMPT, max_tokens=32)

    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        client.generate(model=model, prompt=_PROMPT, max_tokens=32)
        samples.append((time.perf_counter() - t0) * 1000)

    result = {
        "metric": "ttft_full_response_ms",
        "note": "non-streaming proxy until Phase 12.4 streaming lands",
        "date": date.today().isoformat(),
        "model": model,
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
    if not _live():
        print("skipped: set OLLAMA_LIVE=1 to run the live TTFT bench")
        return
    parser = argparse.ArgumentParser(description="Ollama TTFT benchmark")
    parser.add_argument("--n", type=int, default=5, help="number of measured runs")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="JSON output path")
    args = parser.parse_args()
    result = run(n=args.n, out_path=args.out)
    if result is None:
        return
    print(
        f"TTFT proxy (n={result['n']}, model={result['model']}): "
        f"median={result['median_ms']}ms  p95={result['p95_ms']}ms  "
        f"min={result['min_ms']}ms  max={result['max_ms']}ms"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
