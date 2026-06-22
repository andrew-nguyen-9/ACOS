"""Time-to-first-token (TTFT) benchmark against live Ollama.

Fires one warm-up `generate` (loads the model into memory) then N measured
streaming calls, timing the latency to the *first streamed chunk* off the model.
Reports median / p95 in ms.

Phase 12.4: measures true streaming-path TTFT — the first NDJSON chunk off
`/api/generate` `stream:True`, then stops iterating (which closes the socket,
freeing the Ollama job). Previously this measured time-to-full-response as an
upper-bound proxy; the streaming path makes the headline metric real. NOTE: this
is the first *chunk*, not the first visible answer token — for a reasoning model
(qwen3) the latter is dominated by a multi-second thinking phase that streaming
cannot shorten; isolating that is 12.5 calibration. See the _PROMPT comment.

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
_NUM_PREDICT = 64
# TTFT = time to the first streamed chunk off the model. We time the first NDJSON
# line, NOT the first non-empty `.response` delta: qwen3 is a reasoning model and
# emits a multi-second stream of empty-`response` "thinking" chunks first, so
# "first visible answer token" is reasoning-bound (~10s+) and measures model
# cognition, not the streaming path. The first *chunk* isolates the path latency
# that the 12.4 streaming work targets. (`generate_stream` filters thinking for the
# UI by design; precise visible-token calibration with think=false is 12.5.)


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = ceil(0.95 * len(ordered)) - 1
    return ordered[max(idx, 0)]


def _live() -> bool:
    # ponytail: skip if OLLAMA_LIVE unset — no live-Ollama CI by design (roadmap §3).
    return bool(os.environ.get("OLLAMA_LIVE"))


async def _measure_ttft(client: OllamaClient, model: str, n: int) -> list[float]:
    """Time to the first streamed NDJSON chunk off the model, per run (ms).

    Uses the same async streaming path as `generate_stream` (httpx
    `AsyncClient.stream` over `/api/generate` `stream:True`) but breaks on the
    first line of any kind, so the number is the streaming-path TTFT rather than
    qwen3's reasoning latency. Exiting the `async with` closes the socket, freeing
    the Ollama job — the same cancellation the disconnect path relies on.
    """
    import time

    import httpx

    url = client._base_url + "/api/generate"  # noqa: SLF001 — bench, same-package
    payload = {
        "model": model,
        "prompt": _PROMPT,
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": _NUM_PREDICT},
    }
    samples: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as http:
            async with http.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for _line in resp.aiter_lines():
                    if _line.strip():
                        break  # first chunk off the model
        samples.append((time.perf_counter() - t0) * 1000)
    return samples


async def _measure_visible_ttft(client: OllamaClient, model: str, n: int) -> list[float]:
    """Time to the first *visible* answer token under ``think:false``, per run (ms).

    This is the metric 12.5 calibration actually moves: with thinking enabled,
    qwen3 streams a multi-second run of empty-`response` chunks before the first
    visible token; `think:false` collapses that gap. We break on the first
    non-empty `.response` delta (not the first chunk). NOT comparable to the
    first-chunk baseline — different metric.
    """
    import time

    import httpx

    url = client._base_url + "/api/generate"  # noqa: SLF001 — bench, same-package
    payload = {
        "model": model,
        "prompt": _PROMPT,
        "stream": True,
        "think": False,
        "options": {"temperature": 0.3, "num_predict": _NUM_PREDICT},
    }
    samples: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as http:
            async with http.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for _line in resp.aiter_lines():
                    if not _line.strip():
                        continue
                    try:
                        delta = json.loads(_line).get("response", "")
                    except json.JSONDecodeError:
                        continue
                    if delta:
                        break  # first visible answer token
        samples.append((time.perf_counter() - t0) * 1000)
    return samples


def run(n: int = 5, out_path: Path | None = _DEFAULT_OUT) -> dict | None:
    import asyncio

    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url)
    if not client.is_available():
        print(f"skipped: Ollama not reachable at {settings.ollama_base_url}")
        return None

    model = settings.default_model
    # Warm-up: load the model into memory so the measured runs are warm TTFT.
    client.generate(model=model, prompt=_PROMPT, max_tokens=32)

    samples = asyncio.run(_measure_ttft(client, model, n))
    visible = asyncio.run(_measure_visible_ttft(client, model, n))

    result = {
        "metric": "ttft_first_chunk_ms",
        "note": "streaming-path TTFT: first NDJSON chunk off the model (Phase 12.4)",
        "date": date.today().isoformat(),
        "model": model,
        "n": n,
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(_p95(samples), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "samples": [round(s, 3) for s in samples],
        # 12.5: the user-facing latency — first *visible* token with think:false.
        "visible_token_think_false": {
            "metric": "ttft_visible_token_ms",
            "note": "first non-empty .response delta under think:false (Phase 12.5)",
            "median_ms": round(statistics.median(visible), 3),
            "p95_ms": round(_p95(visible), 3),
            "min_ms": round(min(visible), 3),
            "max_ms": round(max(visible), 3),
            "samples": [round(s, 3) for s in visible],
        },
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
        f"TTFT first-chunk (n={result['n']}, model={result['model']}): "
        f"median={result['median_ms']}ms  p95={result['p95_ms']}ms  "
        f"min={result['min_ms']}ms  max={result['max_ms']}ms"
    )
    vis = result["visible_token_think_false"]
    print(
        f"TTFT visible-token think:false (n={result['n']}): "
        f"median={vis['median_ms']}ms  p95={vis['p95_ms']}ms  "
        f"min={vis['min_ms']}ms  max={vis['max_ms']}ms"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
