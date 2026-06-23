# Phase 12.2 — Async Runtime (uvloop + aiosqlite + Async Sessions)

**Track:** Velocity · **Depends on:** 12.0, 12.1 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** PY-001, PY-002, Ollama rec #4

> Largest velocity refactor. Touches the data-access layer broadly — do it before the flywheel adds
> more repositories. Use the strangler pattern; keep tests green at every step.

## 1. Context

`backend/database.py` uses sync `create_engine` + `Session`; repositories use sync sessions; routes
are `def` or `async def` calling sync repos (blocking the event loop). Streaming (12.4) stutters when
a sync DB write runs mid-stream. Migrate to `sqlite+aiosqlite` + `AsyncSession`.

## 2. Goals

- `uvloop.install()` at the FastAPI entry point (`server_entry.py` / `main.py` lifespan start).
- `create_async_engine("sqlite+aiosqlite:///…")` + `async_sessionmaker`; reuse `_apply_pragmas` (12.1).
- Convert repositories to async (`async with AsyncSession`) and routes to `async def` + `await`.
- Alembic `env.py` async-compatible (run migrations via `asyncio.run` / `run_sync`).
- Keep a sync engine available **only** for Alembic offline + any startup seed that must be sync.

## 3. Non-goals (YAGNI)

- No ORM model changes; no query-logic changes — mechanical sync→async only.
- No connection-pool tuning beyond defaults (`# ponytail: single-user, default pool is fine`).

## 4. Acceptance criteria

- [ ] App boots on uvloop (log/assert `asyncio.get_event_loop_policy()` is uvloop's).
- [ ] All DB access goes through `AsyncSession`; no sync `Session` in request paths (grep gate in test).
- [ ] Alembic `upgrade head` + `downgrade` work against the async URL (round-trip test from 11.1 still passes).
- [ ] Full existing test suite green (tests migrated to async where they touch the DB).
- [ ] Concurrency bench (12.0 `test_async_latency`) shows p95 improvement vs sync baseline, or no regression with justification.

## 5. Design

- `database.py`: `async_engine`, `AsyncSessionLocal`, `get_async_session()` dependency. Pragmas via
  `connect` event on the sync DBAPI conn underneath aiosqlite.
- Repositories: convert method bodies to `await session.execute(select(...))`; return scalars.
- Routes/services: `async def` end-to-end; `Depends(get_async_session)`.
- Alembic `env.py`: `run_migrations_online` uses `connectable = create_async_engine(...)` + `connection.run_sync(do_run_migrations)`.
- Migration order: introduce async engine alongside sync, convert layer-by-layer (repos → services →
  routes), delete sync request-path engine last.

## 6. File-level plan

```
EDIT backend/server_entry.py / backend/main.py   (uvloop.install + async lifespan)
EDIT backend/database.py                          (async engine/session, reuse _apply_pragmas)
EDIT backend/repositories/*.py                    (async methods)
EDIT backend/services/**                           (await repo calls)
EDIT backend/api/v1/routes/*.py                   (async def + async session dep)
EDIT database/migrations/env.py                   (async online migrations)
EDIT backend/tests/**                              (async test fixtures; httpx AsyncClient)
NEW  backend/tests/unit/test_async_session.py     (session yields, pragmas applied, no sync leak)
ADD  pyproject/deps: uvloop, aiosqlite, sqlalchemy[asyncio]
```

## 7. Test plan (TDD)

- `test_async_session.py`: `get_async_session` yields an `AsyncSession`; pragmas read back; closes cleanly.
- Grep test: no `from backend.database import SessionLocal` in `api/` or request-path `services/`.
- Convert API tests to `httpx.AsyncClient` + `ASGITransport`.

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLAlchemy 2.0 async (`create_async_engine`, `async_sessionmaker`), aiosqlite, Alembic async `env.py`, uvloop install.
- [ ] `superpowers:test-driven-development` + `systematic-debugging` (async migrations are fiddly).
- [ ] `superpowers:requesting-code-review` (broad blast radius).

## 9. Perf budget impact

Target: better p95 under concurrency; cold start may rise slightly from uvloop import — keep within
12.0's cold-start budget (offset by 12.3 lazy imports). Bench before/after.

## 10. Definition of Done

uvloop active, full async data layer, async Alembic, all tests green, concurrency bench attached, PR reviewed.
