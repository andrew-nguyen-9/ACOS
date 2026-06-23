# Phase 11.1 — Fault Tolerance + Data Integrity

**Track:** Backend · **Depends on:** 11.0 · **Branch:** `feat/phase-11-hardening-and-frontend`
**Status:** Planned

> Read `2026-06-21-phase-11-roadmap.md` first. Global rule in force: stability > optimization;
> no autonomous destructive actions.

---

## 1. Context

Implements brief items **#1 Fault Tolerance** and **#2 Data Integrity**. The system already
degrades for Ollama (templates fallback) and has WAL + FK pragmas (`backend/database.py`), and
a `/health` + `/health/ollama` route. What's missing: structured retry on ingestion, a defined
fallback retrieval mode when Chroma is unavailable, partial-degradation signalling to the UI,
and explicit integrity/consistency validation for SQLite + Chroma + embedding versions.

Current seams:
- `backend/services/ingestion/` pipeline (entity_extractor, normalizer, pipeline, security).
- `backend/rag/` (chroma_client, retriever, embedder, indexer) and `services/rag/service.py`.
- `backend/services/intelligence/multi_vector_retriever.py` (Phase 10 retrieval).
- `database.py` `_enable_wal_and_fk`; Alembic in `database/migrations/`.
- `system_config` table available for storing embedding model/version + integrity status.

## 2. Goals

- **Retry logic** for ingestion (transient failures: file locks, parser hiccups) with bounded
  exponential backoff + dead-letter logging (no infinite loops, no crash).
- **Fallback retrieval mode**: when Chroma is unavailable or empty, RAG degrades to a defined
  mode (keyword/BM25-style over SQLite content or last-known cache) and flags `degraded=true`.
- **Partial degradation handling**: a single `SystemStatus` surface aggregating DB / Chroma /
  Ollama / embedding-version health, consumed by `/health` and the UI banner.
- **SQLite integrity validation**: `PRAGMA integrity_check` + FK check, exposed via a service and
  a `/health/integrity` endpoint (read-only).
- **ChromaDB consistency checks**: collection count vs SQLite document count reconciliation;
  detect orphaned/missing vectors.
- **Embedding version tracking**: record `embedding_model` + a content hash scheme so re-embedding
  can be detected when the model changes; surface "embeddings stale" without auto-rebuilding.
- **Migration rollback safety**: every Alembic migration must have a tested `downgrade()`; add a
  guard + doc + test that asserts upgrade→downgrade→upgrade round-trips on a temp DB.

## 3. Non-goals (YAGNI)

- No automatic re-embedding or re-indexing here — that's a *suggestion* in 11.4 (approval-gated).
- No distributed/multi-node concerns (local-first, single user).
- No new vector backend; keep Chroma.
- Fallback retrieval is "good enough to keep working," not a second ranking engine.

## 4. Acceptance criteria

- [ ] Ingesting a transiently-failing file retries up to N times then logs a dead-letter record and returns a structured error (no crash, no partial corrupt write).
- [ ] With Chroma forcibly unavailable, a RAG query returns results via fallback mode with `degraded=true` and a reason; no 500.
- [ ] `GET /health/integrity` returns SQLite `integrity_check` result, FK violation count, and Chroma↔SQLite doc-count reconciliation.
- [ ] `GET /health` aggregates a `SystemStatus` with per-subsystem state (`ok|degraded|down`).
- [ ] `embedding_model` + version recorded in `system_config`; a check reports "stale" when current model ≠ recorded model.
- [ ] A test runs each migration's upgrade→downgrade→upgrade on a temp SQLite DB and passes.
- [ ] ≥90% coverage on new services; all existing tests green.

## 5. Design

### Retry
- `backend/services/ingestion/retry.py`: `retry(fn, attempts=3, base_delay=0.2, exc=(TransientError,))`
  pure helper (no external dep). Define `TransientError` vs `PermanentError` taxonomy in
  `backend/services/ingestion/errors.py`. Pipeline wraps per-file steps; permanent errors skip
  to dead-letter immediately.
- Dead-letter: append structured record (path, stage, error, ts) via `log_operation` + a
  `ingestion_failures` table (new model + migration) so the UI can list failures.

### Fallback retrieval
- `backend/services/rag/fallback.py`: keyword search over SQLite document/experience text
  (SQLite FTS5 if available, else `LIKE` scan — `# ponytail: LIKE scan, swap to FTS5 if corpus grows`).
- `services/rag/service.py` + `multi_vector_retriever`: try Chroma; on `ChromaUnavailable`/empty,
  call fallback and tag result `degraded`.

### SystemStatus + integrity
- `backend/services/system_status.py`: `collect()` → dataclass with db/chroma/ollama/embedding states.
- `backend/services/integrity.py`: `sqlite_integrity(session)`, `foreign_key_check(session)`,
  `chroma_reconcile(session, chroma)`.
- Routes: extend `health.py` (`/health` aggregates; add `/health/integrity`).

### Embedding version
- Store `embedding_model` (already seeded) + add `embedding_schema_version` to `system_config`.
- `integrity.embedding_status()` compares configured vs recorded; returns `current|stale|unknown`.

### Migration rollback safety
- `backend/tests/integration/test_migration_roundtrip.py`: for each revision, run
  `alembic upgrade head`, `downgrade -1`...`base`, `upgrade head` on a temp file DB; assert no error.
- Add a short note to `database/README.md`: "every migration must define downgrade()."

## 6. File-level plan

```
NEW  backend/services/ingestion/errors.py        (TransientError/PermanentError)
NEW  backend/services/ingestion/retry.py
NEW  backend/services/rag/fallback.py
NEW  backend/services/system_status.py
NEW  backend/services/integrity.py
NEW  backend/models/ingestion_failure.py         (+ register in models/__init__.py)
NEW  database/migrations/versions/<rev>_phase11_ingestion_failures.py
EDIT backend/services/ingestion/pipeline.py      (wrap steps in retry + dead-letter)
EDIT backend/services/rag/service.py             (fallback path + degraded flag)
EDIT backend/services/intelligence/multi_vector_retriever.py (degrade-aware)
EDIT backend/api/v1/routes/health.py             (aggregate SystemStatus + /health/integrity)
EDIT backend/database.py                          (helper: integrity pragmas if needed)
EDIT database/README.md                           (downgrade() requirement note)
NEW  backend/tests/unit/test_retry.py
NEW  backend/tests/unit/test_fallback_retrieval.py
NEW  backend/tests/unit/test_integrity.py
NEW  backend/tests/unit/test_system_status.py
NEW  backend/tests/integration/test_migration_roundtrip.py
```

## 7. Test plan (TDD)

- `test_retry.py`: succeeds after k failures; gives up after N; respects exc taxonomy; backoff bounded.
- `test_fallback_retrieval.py`: Chroma stub raises → fallback returns ranked-ish results + `degraded`.
- `test_integrity.py`: clean DB → ok; inject FK violation/orphan vector → reported; embedding stale path.
- `test_system_status.py`: each subsystem up/down combination aggregates correctly.
- `test_migration_roundtrip.py`: round-trip all revisions on temp DB.

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLAlchemy/Alembic (downgrade patterns), ChromaDB client API, SQLite FTS5/PRAGMA.
- [ ] `superpowers:test-driven-development`.
- [ ] `security-guidance` — ingestion handles user files: confirm path allowlist + size limits + no exec of parsed content still hold (CLAUDE.md security reqs).
- [ ] `superpowers:systematic-debugging` if a migration round-trip fails.
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

Integrity checks are on-demand (health route), not per-request. Retry adds latency only on
failure. Fallback path is slower than Chroma but only runs when Chroma is down. Run 11.0 benches
to confirm no regression on the happy path.

## 10. Risks & mitigations

- *`PRAGMA integrity_check` slow on large DBs* → run only on `/health/integrity`, not `/health`.
- *Fallback quality poor* → acceptable; it's a safety net, flagged `degraded` so UI sets expectations.
- *Down-migrations untested historically* → the round-trip test will surface gaps; fix or document.

## 11. Definition of Done

Retry + dead-letter, fallback retrieval, SystemStatus, integrity endpoints, embedding-version
tracking, and migration round-trip test all implemented, tested ≥90%, existing tests green, PR
with perf delta attached.
