# ADR-007: FastAPI as Backend Framework

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

The system needs a Python backend to orchestrate LLM calls, database access, ChromaDB
operations, and file processing. The backend exposes a REST API consumed by the Tauri
frontend.

---

## Decision

Use **FastAPI** as the backend framework with **Pydantic v2** for request/response
validation and **SQLAlchemy 2.0** for ORM.

---

## Consequences

**Positive:**
- FastAPI auto-generates OpenAPI docs (useful for development)
- Pydantic v2 provides fast, type-safe request validation
- Async support aligns with streaming LLM responses
- Python type hints throughout (compatible with pyright)
- Largest Python REST framework ecosystem
- ASGI-based; deployable with uvicorn

**Negative:**
- Async Python has subtle bugs (mixing sync/async SQLAlchemy, blocking calls)
- Heavier than Flask for simple endpoints

**Mitigations:**
- Use `context7` for FastAPI async patterns before any async implementation
- All database operations use `asyncpg`-compatible async SQLAlchemy session
- Background tasks (ingestion, re-indexing) run in FastAPI `BackgroundTasks` or separate threads

---

## API Structure

```
/api/v1/
├── health/
├── ingest/
├── documents/
├── experiences/
├── projects/
├── skills/
├── applications/
├── resume/
│   ├── generate
│   └── analyze-ats
├── cover-letter/
│   ├── generate
│   └── learn-voice
├── questions/
├── answers/
├── copilot/
│   └── chat
├── analytics/
│   └── outcomes
└── config/
```

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Django | Too heavyweight; ORM conflicts with SQLAlchemy preference |
| Flask | No async support; manual OpenAPI; less type-safe |
| Litestar | Less mature; smaller community |
| aiohttp | Lower-level; manual routing |
