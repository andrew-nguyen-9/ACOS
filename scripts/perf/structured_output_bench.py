"""Phase 12.8 Spike A — structured-output fuzz bench against live Ollama.

Measures the spike's claim directly: feeding N varied resume snippets through the
entity-extraction prompt, how often does the raw model output parse as valid JSON?

- Baseline arm (flag OFF): current production path — no ``format``, reasoning on.
  qwen3 wraps answers in a ``<think>`` block and free prose, so ``json.loads``
  fails and the route falls back to empty/regex (a "retry"/parse-error).
- Structured arm (flag ON): ``format`` = JSON Schema + ``think=False``. Ollama
  constrains the output to the schema, so every response is valid JSON.

Reports valid-JSON count and parse-error count per arm. The accept gate is the
structured arm at 100% valid / 0 parse-errors while the baseline shows failures.

Opt-in (needs a running Ollama with the default model pulled):

    OLLAMA_LIVE=1 python scripts/perf/structured_output_bench.py            # N=50
    OLLAMA_LIVE=1 python scripts/perf/structured_output_bench.py --n 20

OLLAMA_LIVE unset → prints "skipped", exits 0 (live-Ollama CI is out of scope).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import date
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import get_settings  # noqa: E402
from backend.ingestion.entity_extractor import _EXTRACT_SCHEMA, _load_prompt  # noqa: E402
from backend.services.ollama_client import OllamaClient  # noqa: E402

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "structured_output.json"

# 50 varied snippets: role × tech × tenure, enough lexical variety to exercise the
# parser without a corpus file (ponytail: generated, not a fixture to maintain).
_ROLES = ["data engineer", "product manager", "backend developer", "ML engineer", "analyst"]
_TECH = ["Python and SQL", "React and TypeScript", "AWS and Terraform", "PyTorch", "Tableau"]
_VERBS = ["built", "led", "shipped", "owned", "scaled", "migrated", "automated", "designed", "optimized", "launched"]


def _snippets(n: int) -> list[str]:
    out = []
    for i in range(n):
        role = _ROLES[i % len(_ROLES)]
        tech = _TECH[(i // len(_ROLES)) % len(_TECH)]
        verb = _VERBS[i % len(_VERBS)]
        years = 2 + (i % 8)
        out.append(
            f"{role.title()} with {years} years of experience. {verb.title()} systems "
            f"using {tech}, {verb} cross-functional initiatives, and improved delivery."
        )
    return out


def _live() -> bool:
    return bool(os.environ.get("OLLAMA_LIVE"))


def _arm(client: OllamaClient, model: str, prompt_cfg: dict, snippets: list[str], *, structured: bool) -> dict:
    """Run one arm; count how many raw responses parse as valid JSON."""
    system = prompt_cfg.get("system", "")
    user_tmpl = prompt_cfg.get("user_template", "{text}")
    fmt = _EXTRACT_SCHEMA if structured else None
    valid = 0
    parse_errors = 0
    timeouts = 0
    for text in snippets:
        user = user_tmpl.format(document_type="resume", text=text)
        try:
            raw = client.generate(
                model=model, prompt=user, temperature=0.1, system=system,
                output_format=fmt, think=False if fmt else None,
            )
        except httpx.TimeoutException:
            # A timeout is a real failure: the route falls back to empty/regex.
            timeouts += 1
            continue
        try:
            json.loads(raw)
            valid += 1
        except json.JSONDecodeError:
            parse_errors += 1
    return {
        "valid_json": valid,
        "parse_errors": parse_errors,
        "timeouts": timeouts,
        "failures": parse_errors + timeouts,
        "n": len(snippets),
    }


def run(n: int = 50, out_path: Path | None = _DEFAULT_OUT) -> dict | None:
    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url)
    if not client.is_available():
        print(f"skipped: Ollama not reachable at {settings.ollama_base_url}")
        return None

    model = settings.default_model
    prompt_cfg = _load_prompt()
    snippets = _snippets(n)
    client.generate(model=model, prompt="warm up", max_tokens=8)  # load model

    baseline = _arm(client, model, prompt_cfg, snippets, structured=False)
    structured = _arm(client, model, prompt_cfg, snippets, structured=True)

    result = {
        "metric": "structured_output_valid_json_rate",
        "note": "entity-extraction prompt: raw-response JSON validity, flag off vs on",
        "date": date.today().isoformat(),
        "model": model,
        "n": n,
        "baseline_flag_off": baseline,
        "structured_flag_on": structured,
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    if not _live():
        print("skipped: set OLLAMA_LIVE=1 to run the live structured-output bench")
        return
    parser = argparse.ArgumentParser(description="Structured-output fuzz bench")
    parser.add_argument("--n", type=int, default=50, help="number of fuzz inputs per arm")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="JSON output path")
    args = parser.parse_args()
    result = run(n=args.n, out_path=args.out)
    if result is None:
        return
    b, s = result["baseline_flag_off"], result["structured_flag_on"]
    print(f"baseline (flag off): {b['valid_json']}/{b['n']} valid JSON, "
          f"{b['parse_errors']} parse-errors, {b['timeouts']} timeouts")
    print(f"structured (flag on): {s['valid_json']}/{s['n']} valid JSON, "
          f"{s['parse_errors']} parse-errors, {s['timeouts']} timeouts")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
