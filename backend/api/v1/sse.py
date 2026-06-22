"""Server-Sent-Events framing for streamed LLM generation (Phase 12.4).

# ponytail: raw `data: {json}\n\n` over StreamingResponse — no sse-starlette until
# reconnect/event-id is actually needed (spec §3).
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol

logger = logging.getLogger(__name__)


class _Disconnectable(Protocol):
    async def is_disconnected(self) -> bool: ...


async def sse_status_stream(
    request: _Disconnectable,
    snapshot: Callable[[], dict | None],
    terminal: set[str],
    *,
    poll_seconds: float = 0.25,
) -> AsyncIterator[str]:
    """Stream a job's status as SSE frames until it reaches a terminal state.

    Reuses the 12.4 framing (``data: {json}\\n\\n``) and disconnect handling.
    ``snapshot()`` returns the current job dict (or ``None`` if it vanished); a
    frame is emitted only when ``status`` changes, and the stream closes once the
    status is in ``terminal``. Honours client disconnect within one poll.
    """
    import asyncio

    last: str | None = None
    while True:
        if await request.is_disconnected():
            return
        job = snapshot()
        if job is None:
            yield f"data: {json.dumps({'error': 'unknown_job'})}\n\n"
            return
        status = job.get("status")
        if status != last:
            yield f"data: {json.dumps(job)}\n\n"
            last = status
        if status in terminal:
            return
        await asyncio.sleep(poll_seconds)


async def sse_token_stream(
    request: _Disconnectable,
    tokens: AsyncIterator[str],
    on_complete: Callable[[str], Awaitable[None]] | None = None,
) -> AsyncIterator[str]:
    """Frame an async token stream as SSE events, honouring client disconnect.

    Emits ``data: {"delta": "..."}\\n\\n`` per token, then a terminal
    ``data: {"done": true}\\n\\n``. Before each token it checks
    ``request.is_disconnected()``; on disconnect it stops within one chunk and
    returns *without* a terminal event and *without* calling ``on_complete`` — so
    a half-generated result is never persisted (the 12.2 async-boundary trap).
    ``on_complete`` runs only on a clean finish, with the request's DB session
    still open.
    """
    parts: list[str] = []
    try:
        async for delta in tokens:
            # Checked after each token is pulled (not before the first), so a stream
            # that yields nothing still terminates cleanly; a disconnect costs at most
            # one already-generated token — within spec §4's "within one chunk".
            if await request.is_disconnected():
                logger.info(
                    "sse_token_stream: client disconnected after %d tokens — aborting", len(parts)
                )
                return
            parts.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"
    except Exception as exc:
        # Headers/200 are already flushed once streaming starts, so an upstream
        # failure (Ollama 500, dropped socket) can't become an HTTP error code.
        # Emit a distinct error frame so the client can tell failure from success,
        # and skip on_complete — a partial/failed result must never be persisted.
        logger.warning("sse_token_stream: upstream generation failed: %s", exc)
        yield f"data: {json.dumps({'error': 'generation_failed'})}\n\n"
        return
    if on_complete is not None:
        await on_complete("".join(parts))
    yield f"data: {json.dumps({'done': True})}\n\n"
