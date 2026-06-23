"""Phase 13.7 — consent-gated model pull with streamed progress."""
from __future__ import annotations

from backend.services.ollama_client import OllamaClient


def test_pull_streams_progress_then_done(client, monkeypatch):
    async def fake_pull(self, model):  # noqa: ANN001
        yield {"status": "pulling manifest"}
        yield {"status": "downloading", "completed": 50, "total": 100}
        yield {"status": "success"}

    monkeypatch.setattr(OllamaClient, "pull_stream", fake_pull)
    resp = client.get("/api/v1/ollama/pull?model=qwen3:8b")
    assert resp.status_code == 200
    body = resp.text
    assert "downloading" in body
    assert '"completed": 50' in body
    assert '"done": true' in body  # terminal frame the FE waits for


def test_pull_emits_error_frame_on_failure(client, monkeypatch):
    async def boom(self, model):  # noqa: ANN001
        raise RuntimeError("ollama unreachable")
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(OllamaClient, "pull_stream", boom)
    resp = client.get("/api/v1/ollama/pull?model=x")
    assert resp.status_code == 200
    assert '"error"' in resp.text  # degraded, not a 500
