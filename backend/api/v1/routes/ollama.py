"""Phase 13.7 — consent-gated Ollama model pull with streamed progress.

A thin SSE proxy over Ollama's POST /api/pull. The pull is **always** user-initiated
(a multi-GB download is never silent — the wizard shows a Download button); this route
only streams progress once the user has consented. Failures surface as an inline error
frame, not a 500, so the wizard can degrade gracefully rather than hard-block.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.services.ollama_client import OllamaClient

router = APIRouter(tags=["ollama"])


@router.get("/ollama/pull")
async def ollama_pull(model: str, request: Request) -> StreamingResponse:
    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url, timeout=None)

    async def gen():
        try:
            async for progress in client.pull_stream(model):
                if await request.is_disconnected():
                    return
                yield f"data: {json.dumps(progress)}\n\n"
            yield f"data: {json.dumps({'status': 'done', 'done': True})}\n\n"
        except Exception as exc:  # ollama down / model name bad — degrade, don't 500
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
