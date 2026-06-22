# Phase 11.2 — Prompt Version Locking + Observability Layer

**Track:** Backend · **Depends on:** 11.0 (and 11.1 for SystemStatus reuse) · **Status:** Planned

> Read the roadmap index first. Global rules: no autonomous changes; rollback must be possible.

---

## 1. Context

Implements brief items **#3 Prompt Version Locking** and **#4 System Observability**.

Current state:
- `backend/services/prompt_loader.py` reads `prompts/<name>.yaml` and returns `version` (default
  "1.0") but does **not** enforce immutability, track active versions, or support rollback/A-B.
- Phase 8 already has `services/optimization/ab_testing.py` and `prompt_evolver.py` — 11.2 must
  integrate with, not duplicate, that machinery. Prompt evolution proposes; 11.2 governs versioning.
- `observability.py` only has request timing + `log_operation`. No drift tracking, no metrics store.
- `optimization` models exist (`backend/models/optimization.py`, 5.3K) — check before adding tables.

## 2. Goals

### Prompt version locking
- Prompts are **versioned** (content-addressed) and **immutable once deployed**: a deployed version
  is frozen as a stored artifact; edits create a new version, never mutate an existing one.
- An **active-version pointer** per prompt name (in `system_config` or a `prompt_version` table).
- **Rollback**: switch the active pointer to any prior version atomically.
- **A/B comparison**: run two versions side-by-side and record outcome metrics keyed by version
  (reuse `ab_testing.py`; this segment supplies version identity + persistence).

### Observability / drift
- Track drift over time for: **retrieval quality**, **ATS score**, **interview conversion**,
  **embedding drift**, **prompt performance**.
- A **metrics store** (append-only table) + a read API to compute rolling baselines and deltas.
- A drift **report** endpoint that flags metrics exceeding a configurable threshold vs baseline.
- Drift detection only **reports**; any remediation is a 11.4 approval-gated suggestion.

## 3. Non-goals (YAGNI)

- No automatic prompt switching on drift (suggest-only → 11.4).
- No external analytics/telemetry (local-only).
- No re-implementation of A/B assignment logic already in `ab_testing.py`.
- No statistical significance engine beyond simple rolling mean + threshold (note upgrade path).

## 4. Acceptance criteria

- [ ] Editing a prompt and "deploying" it creates version N+1; version N's stored content is unchanged.
- [ ] `PromptLoader.load(name)` resolves the **active** version; `load(name, version=...)` pins one.
- [ ] `rollback(name, to_version)` switches active pointer; subsequent loads use the old version.
- [ ] A deployed version's stored artifact is immutable — a test proves attempting to overwrite raises.
- [ ] Metrics can be recorded (`record_metric(kind, value, meta)`) and queried as a time series.
- [ ] `GET /observability/drift` returns each metric's baseline, current rolling value, delta, and `drifting: bool`.
- [ ] A/B run records outcomes tagged with prompt name+version; comparison report retrievable.
- [ ] ≥90% coverage on new code; existing optimization tests green.

## 5. Design

### Prompt versioning
- Store deployed prompt artifacts as files under `backend/prompts/_versions/<name>/<version>.yaml`
  (content-addressed: `version = vN` with a recorded sha256), OR a `prompt_version` table holding
  `(name, version, content_sha, content, created_at, deployed)`. **Recommended: table** (atomic
  pointer, easy rollback, immutability enforced by app + no UPDATE on content).
- `backend/services/prompts/registry.py`: `deploy(name, content)`, `active(name)`, `get(name, version)`,
  `rollback(name, version)`, `list_versions(name)`. Immutability: content column never UPDATEd;
  `deploy` always INSERTs; a test asserts no code path mutates an existing row's content.
- `prompt_loader.py`: prefer registry's active version; fall back to the on-disk yaml (current
  behavior) if the prompt was never deployed to the registry — keeps existing prompts working.
- Active pointer: `prompt_active` table or `system_config` key `prompt_active::<name> = vN`.

### Observability / drift
- `backend/models/metric.py` → `metric` table: `(id, kind, value REAL, meta JSON, created_at)`.
  `kind ∈ {retrieval_quality, ats_score, interview_conversion, embedding_drift, prompt_perf}`.
- `backend/services/observability/metrics.py`: `record(kind, value, meta)`, `series(kind, since)`,
  `rolling(kind, window)`.
- `backend/services/observability/drift.py`: `report()` → for each kind compute baseline (first
  window mean) vs current rolling mean; `drifting = abs(delta) > threshold` (threshold in
  `system_config`, per kind). `embedding_drift` = mean cosine distance between re-embedded sample
  set and stored vectors (sampled, cheap).
- Route `backend/api/v1/routes/observability.py`: `GET /observability/drift`, `GET /observability/metrics?kind=`.
- Hook existing engines to emit metrics: ATS scorer → `ats_score`; retriever → `retrieval_quality`
  (e.g., top-k score); strategy/outcome learner → `interview_conversion`. Emit via `metrics.record`
  at natural points; keep it additive and cheap.

## 6. File-level plan

```
NEW  backend/models/prompt_version.py        (+ active pointer; register in models/__init__.py)
NEW  backend/models/metric.py
NEW  database/migrations/versions/<rev>_phase11_prompt_versions_metrics.py
NEW  backend/services/prompts/__init__.py
NEW  backend/services/prompts/registry.py
NEW  backend/services/observability/__init__.py
NEW  backend/services/observability/metrics.py
NEW  backend/services/observability/drift.py
NEW  backend/api/v1/routes/observability.py   (+ include_router in main.py)
EDIT backend/services/prompt_loader.py        (resolve active version via registry, fallback to disk)
EDIT backend/main.py                          (register observability router)
EDIT backend/services/ats/scorer.py           (emit ats_score metric)
EDIT backend/services/intelligence/multi_vector_retriever.py (emit retrieval_quality)
EDIT backend/services/optimization/ab_testing.py (tag runs with prompt name+version)
NEW  backend/tests/unit/test_prompt_registry.py
NEW  backend/tests/unit/test_metrics.py
NEW  backend/tests/unit/test_drift.py
NEW  backend/tests/integration/test_prompt_rollback.py
```

## 7. Test plan (TDD)

- `test_prompt_registry.py`: deploy→v1; deploy again→v2; active=v2; rollback v1→active=v1;
  immutability (overwrite attempt raises / no mutation path); unknown version errors.
- `test_metrics.py`: record/series/rolling correctness; meta JSON round-trips.
- `test_drift.py`: synthetic series within threshold → not drifting; beyond → drifting; embedding
  drift on a stubbed embedder.
- `test_prompt_rollback.py` (integration): loader returns rolled-back content end-to-end.

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLAlchemy JSON columns, Alembic; ChromaDB sampling for embedding drift.
- [ ] `superpowers:test-driven-development`.
- [ ] `commit-commands` / version safety — prompts are now versioned artifacts; commit registry seed.
- [ ] `claude-md-management` — document the prompt-versioning workflow (update `docs/05_PROMPT_LIBRARY.md`).
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

`PromptLoader` gains one indexed lookup per load (cache active-version map in-process, invalidate on
deploy/rollback). Metric `record()` is a single INSERT — keep off hot loops or batch. Drift report
is on-demand. Confirm with 11.0 benches.

## 10. Risks & mitigations

- *Double source of truth (disk yaml vs registry)* → registry authoritative once deployed; disk is
  the seed/default. Document clearly; a migration can import existing yamls as v1.
- *Metric writes on hot path* → only emit at coarse boundaries; batch if benches show cost.
- *Naive drift threshold* → `# ponytail: rolling-mean threshold; add CUSUM/z-score if false alarms`.

## 11. Definition of Done

Versioned immutable prompts with rollback + A/B identity; metrics store + drift report endpoints;
engines emit metrics; `docs/05_PROMPT_LIBRARY.md` updated; ≥90% coverage; PR with perf delta.
