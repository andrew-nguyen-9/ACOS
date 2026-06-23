# Phase 12.10 — Local Feedback-Loop Engine

**Track:** Flywheel · **Depends on:** 12.2; **strongly prefers** 12.14 first (tenant-scoped storage)
**Branch:** `feat/phase-12-velocity-flywheel-multitenant` · **Status:** Planned

> First flywheel segment. Captures per-user outcome signals so every later flywheel piece has data.
> If 12.14 hasn't landed, write all new tables with a `tenant_id` column (nullable now, see 12.14).

## 1. Context

Models already exist for `outcome`, `metric`, `memory`, and a `learning/` service (outcome ranking)
plus `optimization/` (A/B + guardrails from Phase 8/11). What's missing is a coherent **feedback loop
engine** that turns raw events (a resume sent, an ATS score, an interview result, a skill used) into
normalized **signals** the ROI engine (12.11) and prompt evolution (12.13) consume.

## 2. Goals

- Define a **signal schema**: `(tenant_id, entity_type, entity_id, signal_type, value, weight, ts, source)`
  covering resume performance, ATS scores, interview outcomes, skill effectiveness.
- **Ingest outcomes** from existing surfaces (ATS scoring route, application/outcome models) into signals.
- A **local aggregation service**: per-user rollups (e.g. skill → avg ATS lift) materialized for fast reads.
- Everything **explainable**: each derived signal links back to its source records (CLAUDE.md confidence system).

## 3. Non-goals (YAGNI)

- No cross-user anything (that's 12.15, gated by the privacy boundary).
- No prompt mutation here (12.13).
- No ML model — start with transparent correlations/rollups (`# ponytail: descriptive stats first; add a model only if they fall short`).

## 4. Acceptance criteria

- [x] `signals` table + model + migration, tenant-scoped, source-linked. — `backend/models/signal.py`, migration `c4d5e6f7a8b9` (`tenant_id` nullable until 12.14, no FK to drop). Up/down round-trip verified in isolation (`ACOS_DB_PATH` temp db).
- [x] Outcome events (ATS score recorded, interview result entered) create signals automatically. — thin best-effort emits in `OutcomeRanker.record_outcome` (source = `outcome_signals` row id) and `_emit_ats_metric` (source = `metrics` row id).
- [x] `feedback.rollup(tenant_id)` returns per-skill / per-section aggregates with sample counts (`avg_value`, `avg_weight`, `n`). On-demand descriptive stats (`# ponytail` ceiling noted).
- [x] Every signal exposes its source record ids via `explain(signal_id)`; `record_signal` refuses an empty source (orphans unrepresentable).
- [x] Engine coverage 100% (`feedback.py` + `signal.py`); full suite 945 passed, 93.55% (≥90%).

**Status: DONE.** Path taken: 12.14 not shipped → `tenant_id` nullable. No ADR: spec §5/§9 settle ingestion-coupling (thin inline emit in existing `run_sync` write paths). No new dependency, no new threadpool (reuses 12.2 runtime).

## 5. Design

- `backend/models/signal.py` + migration.
- `backend/services/flywheel/feedback.py`: `record_signal(...)`, `rollup(tenant_id)`, `explain(signal_id)`.
- Hook into existing ATS/outcome write paths to emit signals (thin, no logic duplication).
- Reuse `learning/` ranking where it already computes outcome scores.

## 6. File-level plan

```
NEW  backend/models/signal.py                 (+ register)
NEW  database/migrations/versions/<rev>_phase12_signals.py
NEW  backend/services/flywheel/__init__.py
NEW  backend/services/flywheel/feedback.py
EDIT backend/services/ats/* , outcome write paths   (emit signals)
NEW  backend/tests/unit/test_feedback_engine.py
NEW  backend/tests/integration/test_signal_ingestion.py
```

## 7. Test plan (TDD)

- `test_feedback_engine.py`: record signals → rollup math correct; `explain` returns source ids.
- `test_signal_ingestion.py`: recording an ATS score creates the expected signal row, tenant-scoped.

## 8. Plugin orchestration checklist

- [ ] `ralph-skills` — skill-effectiveness signal modeling scaffolding.
- [ ] `superpowers:test-driven-development`.
- [ ] `explanatory-output-style` — signal explanations are user-facing; keep them traceable.

## 9. Perf budget impact

Signal writes are small + async (12.2). Rollups materialized/cached; computed on write or on demand with cache.

## 10. Definition of Done

Signal schema + ingestion + rollups + explainability, tenant-scoped, tested ≥90%, existing tests green, PR.
