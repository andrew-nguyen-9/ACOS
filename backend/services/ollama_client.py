import json
import logging
import math
from collections.abc import AsyncIterator
from enum import Enum

import httpx

logger = logging.getLogger(__name__)

_GENERATE_PATH = "/api/generate"
_EMBED_PATH = "/api/embeddings"
_EMBED_BATCH_PATH = "/api/embed"  # plural-response batch endpoint (distinct from /api/embeddings)
_TAGS_PATH = "/api/tags"
_PULL_PATH = "/api/pull"

# 12.5 calibration defaults. num_thread pins to the M1 performance-core count;
# keep_alive holds the generator warm to avoid idle-unload cold starts.
DEFAULT_NUM_THREAD = 4  # ponytail: 4 P-cores; a setting, not hardware auto-probing
DEFAULT_KEEP_ALIVE = "1h"

_MIN_CTX = 2048
_CTX_GRANULARITY = 2048


class Operation(str, Enum):
    """Generation operation → context-window cap.

    Caps are uniform at 4096 today (the 16GB swap-cliff ceiling); the enum is the
    per-operation tuning point — raise/lower one cap here, not at every call site.
    """

    DEFAULT = "default"
    CHAT = "chat"
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


_NUM_CTX_CAP: dict[Operation, int] = {
    Operation.DEFAULT: 4096,
    Operation.CHAT: 4096,
    Operation.RESUME: 4096,
    Operation.COVER_LETTER: 4096,
}


def build_options(
    operation: Operation = Operation.DEFAULT,
    *,
    temperature: float = 0.3,
    max_tokens: int | None = None,
    prompt_tokens: int | None = None,
    num_thread: int = DEFAULT_NUM_THREAD,
) -> dict:
    """Assemble the Ollama ``options`` payload with a calibrated context window.

    When ``prompt_tokens`` is known, size ``num_ctx`` to demand (prompt + answer
    headroom), rounded up to a 2048 bucket and clamped to ``[2048, cap]`` — a
    short retrieval reserves 2048 of KV cache instead of the full 4096.
    """
    cap = _NUM_CTX_CAP.get(operation, 4096)
    if prompt_tokens is None:
        num_ctx = cap
    else:
        needed = prompt_tokens + (max_tokens or 512)
        bucket = _CTX_GRANULARITY * max(1, math.ceil(needed / _CTX_GRANULARITY))
        num_ctx = min(cap, max(_MIN_CTX, bucket))
    opts: dict = {"temperature": temperature, "num_ctx": num_ctx, "num_thread": num_thread}
    if max_tokens is not None:
        opts["num_predict"] = max_tokens
    return opts


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        *,
        num_thread: int = DEFAULT_NUM_THREAD,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._num_thread = num_thread
        self._keep_alive = keep_alive

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        system: str | None = None,
        *,
        operation: Operation = Operation.DEFAULT,
        prompt_tokens: int | None = None,
        think: bool | None = None,
        output_format: dict | None = None,
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": build_options(
                operation,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_tokens=prompt_tokens,
                num_thread=self._num_thread,
            ),
            "keep_alive": self._keep_alive,
        }
        if system is not None:
            payload["system"] = system
        if think is not None:
            payload["think"] = think
        # 12.8 Spike A: top-level `format` = JSON Schema (Ollama structured output,
        # not GBNF) — constrains output to valid JSON. Threaded like `think`.
        if output_format is not None:
            payload["format"] = output_format

        resp = httpx.post(
            f"{self._base_url}{_GENERATE_PATH}",
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        system: str | None = None,
        *,
        operation: Operation = Operation.DEFAULT,
        prompt_tokens: int | None = None,
        think: bool | None = None,
        output_format: dict | None = None,
    ) -> AsyncIterator[str]:
        """Yield token deltas from Ollama's streaming /api/generate (stream=True).

        Parses NDJSON, emitting each non-empty `.response`. Blank keep-alive and
        malformed lines are skipped, never raised — a stream must not die on one
        bad chunk. The caller stops iterating to cancel (httpx closes the socket,
        freeing the Ollama GPU job).
        """
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": build_options(
                operation,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_tokens=prompt_tokens,
                num_thread=self._num_thread,
            ),
            "keep_alive": self._keep_alive,
        }
        if system is not None:
            payload["system"] = system
        if think is not None:
            payload["think"] = think
        # ponytail: symmetric with generate(); no streaming-JSON caller today
        # (12.4 copilot stream is prose), but keeps the two paths from diverging.
        if output_format is not None:
            payload["format"] = output_format

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._base_url}{_GENERATE_PATH}", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        delta = json.loads(line).get("response", "")
                    except json.JSONDecodeError:
                        logger.debug("generate_stream: skipping malformed line")
                        continue
                    if delta:
                        yield delta

    async def pull_stream(self, model: str) -> AsyncIterator[dict]:
        """Yield progress dicts from Ollama's streaming POST /api/pull.

        Each line is ``{"status": ..., "completed"?: int, "total"?: int}``. Blank
        keep-alive and malformed lines are skipped, never raised — one bad chunk
        must not abort a multi-GB download. No read timeout: a pull is long-lived;
        the caller cancels by stopping iteration (httpx closes the socket).
        """
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self._base_url}{_PULL_PATH}", json={"name": model, "stream": True}
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        logger.debug("pull_stream: skipping malformed line")
                        continue

    def embed(self, model: str, text: str) -> list[float]:
        resp = httpx.post(
            f"{self._base_url}{_EMBED_PATH}",
            json={"model": model, "prompt": text},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def embed_batch(self, model: str, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in one round trip via POST /api/embed.

        Distinct from :meth:`embed`: `/api/embed` takes `input: [list]` and
        returns `embeddings: [[...]]` (plural), one vector per input in order.
        An empty list makes no HTTP call (an empty `input` is a 400).
        """
        if not texts:
            return []
        resp = httpx.post(
            f"{self._base_url}{_EMBED_BATCH_PATH}",
            json={"model": model, "input": texts, "keep_alive": self._keep_alive},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def unload(self, model: str) -> None:
        """Fire-and-forget: free a model's RAM via keep_alive:0 (empty prompt).

        Best-effort — a dead daemon or slow unload must never crash the caller's
        generate path. Used to evict the embedder before the generator runs so the
        two models don't co-reside and blow the 16GB budget.
        """
        try:
            httpx.post(
                f"{self._base_url}{_GENERATE_PATH}",
                json={"model": model, "keep_alive": 0},
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.debug("unload(%s) failed (ignored): %s", model, exc)

    def list_models(self) -> list[str]:
        try:
            resp = httpx.get(f"{self._base_url}{_TAGS_PATH}", timeout=10)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.warning("list_models failed: %s", exc)
            return []
