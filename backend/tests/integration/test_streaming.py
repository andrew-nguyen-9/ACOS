"""Phase 12.4 — SSE streaming + disconnect/cancellation behaviour.

The Ollama stream is stubbed throughout; these tests never touch live Ollama.
They pin: (1) the SSE framing helper emits one event per delta + a terminal
`done`, (2) a mid-stream client disconnect breaks the loop within one chunk and
skips the persist hook (no half-written row — the async-boundary trap), and
(3) the copilot streaming route wires it together into `text/event-stream`.
"""
from __future__ import annotations

import json

from backend.api.v1.sse import sse_token_stream


async def _agen(items):
    for x in items:
        yield x


class _FakeReq:
    """Minimal stand-in for starlette Request.is_disconnected()."""

    def __init__(self, disconnect_after: int | None = None) -> None:
        self._checks = 0
        self._after = disconnect_after

    async def is_disconnected(self) -> bool:
        self._checks += 1
        return self._after is not None and self._checks > self._after


async def test_sse_frames_each_delta_then_done_and_calls_on_complete():
    captured: dict[str, str] = {}

    async def on_complete(full: str) -> None:
        captured["full"] = full

    events = [
        e
        async for e in sse_token_stream(_FakeReq(), _agen(["Hel", "lo"]), on_complete=on_complete)
    ]

    assert events[0] == 'data: {"delta": "Hel"}\n\n'
    assert events[1] == 'data: {"delta": "lo"}\n\n'
    assert json.loads(events[2][len("data: ") :]) == {"done": True}
    assert captured["full"] == "Hello"  # final concat == streamed deltas joined


async def test_sse_disconnect_breaks_within_one_chunk_and_skips_persist():
    persisted: list[str] = []

    async def on_complete(full: str) -> None:
        persisted.append(full)

    # is_disconnected returns True on the 2nd check → only the first delta emits,
    # the loop breaks before the 2nd, and on_complete never runs.
    events = [
        e
        async for e in sse_token_stream(
            _FakeReq(disconnect_after=1), _agen(["a", "b", "c"]), on_complete=on_complete
        )
    ]

    assert events == ['data: {"delta": "a"}\n\n']  # stopped within one chunk, no `done`
    assert persisted == []  # half-written persist skipped — no orphan row


async def test_sse_upstream_error_emits_error_frame_and_skips_persist():
    persisted: list[str] = []

    async def on_complete(full: str) -> None:
        persisted.append(full)

    async def _boom():
        yield "partial"
        raise RuntimeError("ollama exploded mid-stream")

    events = [
        e async for e in sse_token_stream(_FakeReq(), _boom(), on_complete=on_complete)
    ]

    assert events[0] == 'data: {"delta": "partial"}\n\n'
    assert json.loads(events[1][len("data: ") :]) == {"error": "generation_failed"}
    assert all('"done"' not in e for e in events)  # failed stream != completed stream
    assert persisted == []  # partial/failed result never persisted


def _stub_copilot(monkeypatch, deltas: list[str]) -> None:
    from backend.services.copilot.engine import CopilotEngine
    from backend.services.ollama_client import OllamaClient

    async def fake_stream(self, model, prompt, **kw):  # noqa: ANN001
        for tok in deltas:
            yield tok

    monkeypatch.setattr(OllamaClient, "generate_stream", fake_stream)
    monkeypatch.setattr(
        CopilotEngine,
        "prepare",
        lambda self, message, conversation_history=None: (
            "PROMPT",
            {
                "response": "fallback text",
                "intent": "career_advice",
                "confidence": "strong_inference",
                "citations": [],
                "evidence_count": 0,
            },
        ),
    )


def test_copilot_stream_route_emits_sse_events(client, monkeypatch):
    _stub_copilot(monkeypatch, ["Hello", " there"])

    with client.stream(
        "POST", "/api/v1/copilot/chat/stream", json={"message": "hi"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())

    frames = [json.loads(line[len("data: ") :]) for line in body.strip().split("\n\n")]
    assert frames[0]["meta"]["intent"] == "career_advice"  # citations/confidence up front
    deltas = [f["delta"] for f in frames if "delta" in f]
    assert deltas == ["Hello", " there"]
    assert "".join(deltas) == "Hello there"  # concat == non-streamed response
    assert frames[-1] == {"done": True}


def test_copilot_stream_logs_completion_only_after_full_drain(client, monkeypatch):
    """on_complete (the persist seam) fires on clean finish, with a terminal `done`."""
    _stub_copilot(monkeypatch, ["one", "two", "three"])
    logged: list[str] = []
    monkeypatch.setattr(
        "backend.api.v1.routes.copilot.log_operation",
        lambda op, **kw: logged.append(op),
    )

    with client.stream(
        "POST", "/api/v1/copilot/chat/stream", json={"message": "hi"}
    ) as r:
        body = "".join(r.iter_text())

    assert '"done": true' in body
    assert logged == ["copilot_chat_stream"]  # recorded exactly once, on completion
