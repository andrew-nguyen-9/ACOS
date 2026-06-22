# Phase 11.4 — Controlled Autonomous Maintenance + Backup & Recovery

**Track:** Backend · **Depends on:** 11.1 (integrity/status), 11.2 (drift), 11.3 (refresh) · **Status:** Planned

> Read the roadmap index first. **STRICT:** no autonomous destructive actions; every maintenance
> action requires explicit user approval. This is the segment where that rule matters most.

---

## 1. Context

Implements brief items **#7 Autonomous Maintenance Mode (Controlled)** and **#8 Backup & Recovery**.

By now the system can *detect* problems (11.1 integrity, 11.2 drift, 11.1 embedding-stale). 11.4
turns detections into **suggestions** the user approves, and provides the safety net of snapshots
and restore so any approved action is reversible.

Current seams:
- `database/backups/.gitkeep` exists — destination for snapshots.
- `system_status` (11.1), `drift.report()` (11.2), `embedding_status` (11.1), `refresh_embeddings`
  (11.3) are the actions a suggestion can wrap.
- `services/optimization/recommender.py` + `guardrails.py` exist (Phase 8) — reuse the
  suggestion/approval pattern; do not reinvent.

## 2. Goals

### Controlled maintenance
- A **maintenance advisor** that, from current health/drift signals, produces a list of suggested
  actions: re-index, prompt rollback, model switch, embedding refresh.
- Each suggestion is **inert** until the user approves it via an explicit API call (and UI later).
- An **audit log** of suggestions, approvals, and executions (who/what/when/result).
- Executing an approved action **always takes a snapshot first** (auto-restore point).

### Backup & recovery
- **Full system snapshot**: SQLite DB (consistent copy via `VACUUM INTO`/backup API) + Chroma
  directory + prompt registry + `system_config`, into a timestamped archive under `database/backups/`.
- **Incremental backups**: snapshot only changed pieces (DB always; Chroma if changed by hash).
- **Restore points**: list snapshots; restore a chosen one (with confirmation; current state
  snapshotted first so restore itself is reversible).
- **Corruption recovery mode**: if `/health/integrity` reports corruption on startup, enter a safe
  read-only mode and surface a restore prompt instead of crashing.

## 3. Non-goals (YAGNI)

- No scheduled/automatic backups running in the background without consent (offer a manual trigger
  + an opt-in setting; the *scheduler* itself is out of scope — `# ponytail: manual trigger now`).
- No cloud backup (local-first, ADR-001).
- No auto-execution of any suggestion, ever.
- No diff-level incremental for SQLite (full DB copy is fine at this scale; Chroma is the only
  "incremental by hash" piece).

## 4. Acceptance criteria

- [ ] `advisor.suggest()` returns suggestions derived from real health/drift inputs, each with a type, reason, and the exact action it would run.
- [ ] A suggestion does nothing until `approve(suggestion_id)` is called; unapproved execution is rejected.
- [ ] Approving + executing an action writes a snapshot first and records an audit entry with result.
- [ ] `backup.snapshot(full=True)` produces a restorable archive; `backup.restore(id)` round-trips on a temp instance.
- [ ] Incremental snapshot skips an unchanged Chroma store (by hash) and always includes the DB.
- [ ] Simulated corruption → startup enters read-only safe mode and exposes a restore action (no crash).
- [ ] `GET /maintenance/suggestions`, `POST /maintenance/approve`, `GET/POST /backup/*` endpoints exist and are covered.
- [ ] ≥90% coverage; existing tests green.

## 5. Design

### Maintenance advisor
- `backend/services/maintenance/advisor.py`: `suggest(session) -> list[Suggestion]` reading
  `system_status`, `drift.report()`, `integrity.embedding_status()`. Maps signals → action types:
  `{reindex, prompt_rollback, model_switch, embedding_refresh}`.
- `backend/services/maintenance/executor.py`: `approve(id)` + `execute(id)`; **execute snapshots
  first**, then runs the bound action (calls 11.1/11.2/11.3 services), records audit.
- `backend/models/maintenance.py`: `maintenance_suggestion` (id, type, reason, payload JSON, status
  ∈ {suggested, approved, executed, dismissed}, created_at) + `maintenance_audit`.
- Reuse `optimization/guardrails.py` validation style for "is this action safe to offer."

### Backup & recovery
- `backend/services/backup/snapshot.py`: `snapshot(full: bool) -> SnapshotMeta`. DB via SQLite
  online backup API or `VACUUM INTO` (consistent, WAL-safe). Chroma via directory copy guarded by
  a content hash for incremental. Prompt registry + system_config dumped to JSON. Archive =
  `database/backups/<ts>__<full|incr>/` + a `manifest.json` (versions, hashes, app_version).
- `backend/services/backup/restore.py`: `list_snapshots()`, `restore(id)` — snapshot-current-first,
  then swap files atomically (write to temp, move into place), validate integrity post-restore.
- Corruption mode: in `main.py` lifespan, after `init_db()`, run a lightweight integrity probe; if
  it fails, set an app flag `READONLY_RECOVERY` that routes mutating endpoints to 503 + a
  `/recovery/status` and `/backup/restore` remain available.

### Endpoints
- `backend/api/v1/routes/maintenance.py`: `GET /maintenance/suggestions`, `POST /maintenance/approve`,
  `POST /maintenance/execute`, `GET /maintenance/audit`.
- `backend/api/v1/routes/backup.py`: `POST /backup/snapshot`, `GET /backup/list`, `POST /backup/restore`,
  `GET /recovery/status`.

## 6. File-level plan

```
NEW  backend/services/maintenance/__init__.py
NEW  backend/services/maintenance/advisor.py
NEW  backend/services/maintenance/executor.py
NEW  backend/services/backup/__init__.py
NEW  backend/services/backup/snapshot.py
NEW  backend/services/backup/restore.py
NEW  backend/models/maintenance.py            (+ register in models/__init__.py)
NEW  database/migrations/versions/<rev>_phase11_maintenance.py
NEW  backend/api/v1/routes/maintenance.py     (+ include in main.py)
NEW  backend/api/v1/routes/backup.py          (+ include in main.py)
EDIT backend/main.py                          (corruption probe → READONLY_RECOVERY; register routers)
NEW  backend/tests/unit/test_advisor.py
NEW  backend/tests/unit/test_backup_snapshot.py
NEW  backend/tests/integration/test_restore_roundtrip.py
NEW  backend/tests/integration/test_corruption_recovery.py
NEW  backend/tests/unit/test_no_autoexec.py   (asserts unapproved actions never run)
```

## 7. Test plan (TDD)

- `test_advisor.py`: given degraded/drifting inputs → correct suggestion types + reasons; healthy → none.
- `test_no_autoexec.py`: calling execute on a non-approved suggestion raises; advisor never executes.
- `test_backup_snapshot.py`: full snapshot creates manifest + restorable artifacts; incremental skips unchanged Chroma.
- `test_restore_roundtrip.py`: mutate → snapshot → mutate more → restore → state matches snapshot; pre-restore snapshot exists.
- `test_corruption_recovery.py`: corrupt the DB file → startup enters read-only; mutating route → 503; restore works.

## 8. Plugin orchestration checklist

- [ ] `security-guidance` — backups contain personal career data: store local-only, correct perms, no secrets in manifest; restore validates source path (allowlist).
- [ ] `context7` — SQLite online backup API / `VACUUM INTO`, ChromaDB persistence layout.
- [ ] `superpowers:test-driven-development`.
- [ ] `commit-commands` — version safety around the restore/swap logic.
- [ ] `pr-review-toolkit` — release safety review (this segment is the riskiest; run silent-failure-hunter + reliability review).
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

Snapshots are user-triggered, off the request path. Startup gains one lightweight integrity probe —
keep it cheap (not full `integrity_check`; a quick `PRAGMA quick_check` or open-and-select). Confirm
with 11.0 startup bench.

## 10. Risks & mitigations

- *Restore corrupts live data mid-swap* → write-to-temp + atomic move; snapshot-current-first; validate after.
- *Backups grow unbounded* → retention policy (keep last K + manual prune); `# ponytail: keep-last-K, add size cap if needed`.
- *Approval bypass* → single chokepoint: only `executor.execute` runs actions, and it checks status==approved. Tested.

## 11. Definition of Done

Advisor (suggest-only), approval-gated executor with snapshot-before-execute + audit, full/incremental
backup, restore round-trip, corruption read-only recovery — all tested ≥90%, release-safety review run,
existing tests green, PR opened. **This completes the backend hardening track (11.1–11.4).**

## 12. Release-safety review outcome (silent-failure-hunter + reliability)

Fixed before merge:
- **Engine pool vs DB swap** — restore now disposes `backend.database.engine` before the
  `os.replace` and rebuilds it after (`database.reset_engine`), so no pooled handle holds the
  old inode / a deleted WAL.
- **Failure-audit durability** — `executor._fail` commits the `failed` status + audit
  independently, so a re-raised execution failure can't be rolled back by the request session.
- **Incremental-restore Chroma staleness** — restore resolves the Chroma copy from the newest
  snapshot at-or-before the target that physically holds one (an incremental that skipped Chroma
  no longer leaves the live store mismatched while reporting `integrity_ok=True`).
- **Best-effort pre-restore snapshot** — a corrupt *current* DB no longer blocks restore (the
  auto restore point is skipped, `pre_restore_snapshot_id=None`).
- **Atomic-ish swaps** — `_swap_dir` rolls back on a failed rename and reconciles an interrupted
  prior swap; a partial restore raises `RestoreError` naming the restore point; DB swap fsyncs
  the temp file + dir.
- **Crash-mid-swap** — a `.restore_in_progress` sentinel is written before the swaps and removed
  on success; startup (`recovery.check_interrupted_restore`) enters READONLY_RECOVERY if found.
- **Observability** — `probe_integrity`, the snapshot JSON dumps, and the lifespan startup
  handler now log swallowed exceptions; `_hash_dir` tolerates per-file read errors.

Deferred (documented residual risks — out of 11.4 scope):
- **Runtime re-probe** — corruption that occurs *after* startup is not auto-detected; only the
  startup probe + sentinel engage recovery. Upgrade: flip `RECOVERY` from a central handler on
  repeated SQLite `DatabaseError`.
- **Backup retention/quota** — snapshots are unbounded (every executed action takes one); spec §3
  keeps pruning manual. Upgrade: keep-last-K that preserves Chroma-holding fulls referenced by
  incrementals.
- **Concurrency** — no lock on `backups_dir`; the app is single-process local (ADR-001), so
  concurrent snapshot/restore is not a real path today.
- **`quick_check` depth + Chroma validation** — startup uses the cheap probe (budget); restore
  validates DB integrity only, not Chroma consistency.
