# Phase 12.4 — SSE Streaming + Generation Cancellation

**Track:** Velocity · **Depends on:** 12.0, 12.2 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** LLM-001, Ollama rec #3, rec #11

> Critical UX win. Depends on async runtime (12.2) so a mid-stream DB write doesn't block.

## 1. Context

`ollama_client` returns full responses (no `stream=True`); resume/cover-letter routes wait for the
whole generation before responding, locking the UI for seconds. No cancellation: rapid "Generate"
clicks queue heavy Ollama jobs the M1 can't parallelize.

## 2. Goals

- `ollama_client.generate_stream()` reading Ollama `stream=True`, yielding token deltas.
- Convert `/resume/generate` and `/cover-letter` (and copilot chat) to `StreamingResponse`
  (`text/event-stream`).
- Frontend: append tokens to the Zustand store as they arrive (Fetch + `ReadableStreamDefaultReader`).
- **Cancellation:** frontend `AbortController` per generation; aborting a prior request cancels it.
  Backend monitors `request.is_disconnected()`, breaks the stream, sends Ollama a cancel so the GPU frees.

## 3. Non-goals (YAGNI)

- No SSE library if raw `StreamingResponse` suffices (`# ponytail: add sse-starlette only if reconnect/event-id needed`).
- No streaming for non-generative endpoints (ATS scoring etc. stay request/response).

## 4. Acceptance criteria

- [ ] `/resume/generate` streams chunks; first chunk arrives well before completion (test asserts incremental yields).
- [ ] Frontend renders tokens progressively; store concatenates correctly; final state equals non-streamed result.
- [ ] Starting a new generation aborts the in-flight one (no two concurrent Ollama jobs).
- [ ] Client disconnect mid-stream → backend stops reading from Ollama within one chunk (logged).
- [ ] TTFT bench (12.0) records a number; no regression vs the warm baseline target (≤800 ms).

## 5. Design

- `ollama_client.generate_stream(prompt, options) -> AsyncIterator[str]`: httpx async streaming over
  Ollama `/api/generate` `stream=True`, parse NDJSON, yield `.response`.
- Route: `return StreamingResponse(_sse(gen), media_type="text/event-stream")`; `_sse` wraps deltas as
  `data: {json}\n\n` and checks `await request.is_disconnected()` each iteration.
- Frontend `services/`: a `streamGenerate()` helper exposing an async iterator + `AbortController`;
  store action appends. Reuse existing generation store.

## 6. File-level plan

```
EDIT backend/services/ollama_client.py        (generate_stream async iterator)
EDIT backend/api/v1/routes/resume.py          (StreamingResponse + disconnect check)
EDIT backend/api/v1/routes/cover_letter.py    (same)
EDIT backend/api/v1/routes/copilot.py         (stream chat)
EDIT frontend/src/services/*.ts               (streamGenerate + AbortController)
EDIT frontend/src/stores/*.ts                 (incremental append)
NEW  backend/tests/integration/test_streaming.py
NEW  frontend/src/__tests__/stream-store.test.ts
```

## 7. Test plan (TDD)

- `test_streaming.py`: stub Ollama stream of N chunks → route yields N SSE events; simulate disconnect → loop breaks.
- vitest: store append from a mocked ReadableStream produces the full string; abort stops appends.

## 8. Plugin orchestration checklist

- [ ] `context7` — FastAPI `StreamingResponse`, httpx async streaming, Ollama stream API, Fetch ReadableStream.
- [ ] `superpowers:test-driven-development`.

## 9. Perf budget impact

Drops perceived latency dramatically (TTFT vs full-gen). Verify no FPS regression while tokens stream
(frontend long-tasks = 0, Phase 11 gate). Bundle: minimal.

## 10. Definition of Done

Streaming generation + cancellation end-to-end, disconnect handling, TTFT bench, tests green, PR.
