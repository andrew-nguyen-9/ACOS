# Phase 12.1 — SQLite Hot-Path Pragmas (WAL / synchronous / mmap)

**Track:** Velocity · **Depends on:** 12.0 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** DB-001, DB-002, DB-003

> Lowest-effort, high-impact perf win. Ship first.

## 1. Context

`backend/database.py` already enables WAL + FK pragmas (Phase 11.1, `_enable_wal_and_fk`). The brief
asks for WAL (have it), `synchronous=NORMAL`, and `mmap_size=256MB`. This segment **verifies** WAL is
actually on at runtime and **adds** the two missing pragmas, with a guard that they apply on every
new connection (SQLite pragmas are per-connection for some, per-DB for others).

## 2. Goals

- Confirm `journal_mode=WAL` is active (test asserts the pragma read-back).
- Add `PRAGMA synchronous=NORMAL` and `PRAGMA mmap_size=268435456` via the existing connect-event hook.
- Make pragma set a single named function so it is reused by the async engine in 12.2.

## 3. Non-goals (YAGNI)

- No change to schema or migrations.
- No tuning beyond the three documented pragmas (`# ponytail: these three are the known wins; add cache_size only if a bench shows need`).

## 4. Acceptance criteria

- [ ] A test opens a real connection and reads back `journal_mode=wal`, `synchronous=1` (NORMAL), `mmap_size=268435456`.
- [ ] Pragmas applied on every pooled connection (verified by opening two sessions).
- [ ] WAL durability note added to `database/README.md` (NORMAL is safe for WAL; risk is last-txn loss on power cut, acceptable for local desktop).
- [ ] Existing tests green; write-heavy test (bulk insert) shows no correctness regression.

## 5. Design

- Extend `_enable_wal_and_fk` → `_apply_pragmas(dbapi_conn)` setting `journal_mode=WAL`,
  `synchronous=NORMAL`, `mmap_size=268435456`, `foreign_keys=ON`. Registered on SQLAlchemy
  `connect` event for both sync (now) and async (12.2) engines.

## 6. File-level plan

```
EDIT backend/database.py            (rename/extend pragma hook; add synchronous + mmap)
EDIT database/README.md             (WAL + NORMAL durability note)
NEW  backend/tests/unit/test_sqlite_pragmas.py
```

## 7. Test plan (TDD)

- `test_sqlite_pragmas.py`: open session, `SELECT` each pragma, assert expected values; open a second
  session and re-assert (per-connection application).

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLite PRAGMA semantics (which are per-connection vs persistent).
- [ ] `superpowers:test-driven-development`.

## 9. Perf budget impact

Pure win on write latency; mmap reduces read syscalls. Run 12.0 benches to record the delta.

## 10. Definition of Done

Three pragmas applied + verified by test, durability documented, no regression, PR with bench delta.
