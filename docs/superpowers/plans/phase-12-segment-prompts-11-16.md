# Phase 12.11–12.16 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. Each is self-contained and
token-budgeted in the style of the 12.10 prompt. Phase ends at **12.16** (close-out) —
there is no 12.17/12.18.

## Recommended order (dependency-correct)

```
12.11 skill ROI      ← 12.10 ✓ (ready now; pure read-side over rollups)
12.14 tenant isolation ← 12.2 ✓ (land NEXT — stops nullable-tenant debt accruing; backfills signals)
12.12 resume strategy  ← 12.10,12.11 (now tenant-scoped for real)
12.13 prompt evolution ← 12.10,12.11 (versioned/approval-gated; reuses optimization/)
12.15 global aggregation ← 12.11,12.14 (needs ≥2 tenants — strictly after 12.14)
12.16 close-out        ← all shipped
```
Rationale: 12.11/12.12 add **no tenant-owned tables** (read-side compute), so doing 12.11
before 12.14 costs nothing. Land **12.14 second** so 12.12/12.13/12.15 are tenant-real and
12.14's backfill only has to fix `signals` (12.10) — not a pile of later tables. If you'd
rather finish the flywheel first, that's fine too: keep threading `tenant_id: str | None =
None` through every new API (as 12.10 did) and 12.14 wiring stays mechanical.

## Session-wide invariants (true for ALL six — stated once, assume in every prompt)

- **Branch:** `feat/phase-12-velocity-flywheel-multitenant`. 12.10 is HEAD `f50e875` (pushed).
  Each segment = one commit on this branch. **PR is deferred to 12.16** (phase merges to `main`
  at close-out); do NOT open a per-segment PR unless told.
- **ALEMBIC ISOLATION (hard lesson from 12.10):** `database/migrations/env.py` reads
  `get_settings().db_url` (env `ACOS_DB_PATH`) and **IGNORES `DATABASE_URL`**. NEVER run
  `alembic upgrade/downgrade` without `ACOS_DB_PATH=$(mktemp -u).db` — otherwise it mutates the
  real dev `database/acos.db`. Verify every migration up→head AND down→base on a temp db.
- **Dual schema path (12.7):** the app bootstraps via `Base.metadata.create_all` (NOT alembic at
  runtime). So: (a) register every new model in `backend/models/__init__.py` or `create_all`
  won't build it; (b) write BOTH the alembic migration AND ensure create_all covers it; (c)
  virtual/non-ORM tables need an `after_create` DDL hook (see the FTS5 hook in models/__init__.py).
- **Test seam:** `backend/tests/conftest.py` `_SyncSessionBridge` runs `session.run_sync(fn)`
  synchronously against the in-memory `test_session` — so route + service tests share one DB. Use
  `test_session` (sync) for unit/integration; `client` (TestClient) for routes. In-memory SQLite +
  StaticPool, FK pragma ON.
- **12.10 surface you build on:** `backend/services/flywheel/feedback.py` →
  `FeedbackEngine(session).record_signal(*, entity_type, entity_id, signal_type, value, source,
  weight=1.0, tenant_id=None)` (rejects empty `source`), `.rollup(tenant_id=None)` →
  `{"tenant_id", "aggregates":[{entity_type, entity_id, signal_type, avg_value, avg_weight, n}]}`,
  `.explain(signal_id)` → source record ids. Module helper `record_signal(session, **kw)`.
  Table `signals` (model `backend/models/signal.py`): `tenant_id` nullable until 12.14.
- **Rules in force every segment:** CLAUDE.md non-negotiables (no hallucination — every derived
  figure traces to a source record + confidence per ADR-006; read `docs/` before coding; `context7`
  for SQLAlchemy 2.0 / Alembic / Pydantic v2 / Chroma — don't code framework APIs from memory); TDD
  (failing test FIRST, ≥90% coverage on new code, existing suite stays green); Git Attribution (NO
  Claude/Anthropic in commits/PRs/branches); Ponytail (descriptive stats before any model; no
  speculative abstraction — re-justify each new file); Caveman (terse prose; code/commits/security
  normal); Superpowers verification-before-completion (paste real coverage % + pytest output, never
  assert green unseen).
- **Env:** `.venv/bin/python`; cwd drifts → absolute paths. `pyright --pythonpath .venv/bin/python
  <files>` on shipped code (resolves venv imports). Full suite `.venv/bin/python -m pytest`.
  `OLLAMA_LIVE=1` only if a step needs live generation. Plugin orchestration per each spec §8.
- **Token-efficiency:** ONE `context7` batch up front (not per-file). ONE read pass: the segment
  spec §2–§7 + only the files you'll touch — STOP reading once you have the schema + acceptance
  criteria. Do NOT re-read shipped 12.0–12.10 plans (state is in MEMORY.md + the schema doc). Land
  small: ADR-if-real → failing test → migration+model (if any) → engine → thin hooks → green →
  verify with real coverage + pytest output → update spec §4 → commit.

---

## 12.11 — Skill ROI Engine

Implement Phase 12.11 — Skill ROI Engine. Turn the 12.10 signals/rollups into a ranked,
explainable, confidence-aware "highest-ROI skills" view, scoped per tenant.

PRECONDITION: depends on 12.10 (SHIPPED, HEAD `f50e875`). No new table — this is **pure read-side
compute over `FeedbackEngine.rollup()`**. Confirm the rollup shape before coding (it returns
per-`(entity_type, entity_id, signal_type)` `avg_value`/`avg_weight`/`n`); if a skill→outcome join
needs a signal that 12.10 doesn't emit yet, add a THIN emit at the skill-use write path (same
best-effort pattern as 12.10's outcome/ATS hooks) — don't fabricate signals.

Read first (STOP once you have acceptance + the rollup API): (1)
`docs/superpowers/plans/2026-06-22-phase-12-11-skill-roi-engine.md` — the contract (goals §2,
non-goals §3, acceptance §4, file plan §6, TDD §7). (2) `backend/services/flywheel/feedback.py` —
the rollup/explain API you consume. (3) SKIM `backend/services/learning/ranker.py`
(`get_ats_vs_outcome_correlation` already buckets ATS→outcome — REUSE its correlation approach,
don't reinvent) + `docs/adr/ADR-006-evidence-confidence-system.md` (the verified/strong/weak levels).

Order fixed: brainstorm (confirm: ROI = effect-size + n + confidence over rollups, NOT a model) →
ADR? skip — spec §3 settles "no ML, effect-size + n"; no real architecture decision → TDD (golden
fixture FIRST per §7) → implement → verify.

Traps: (1) **Confidence is non-negotiable** — every ROI figure carries n + a confidence level;
low-n skills tagged `weak_inference` and EXCLUDED from "recommended" output (acceptance §4). A
confident-looking ROI on n=1 is the bug. (2) **Explainability** — `rank_skills` output lists the
contributing signal/outcome ids (reuse `explain`); no orphan ROI. (3) **Determinism** — fixed signal
set → identical ranking (golden test); sort ties stably. (4) tenant_id threads through as `str |
None` (12.14 forward-compat); `None` = single-tenant today.

Reuse/current-state: rollups + explain exist (12.10); ranker has the ATS↔outcome correlation
bucketing; optimization/ has effect-size helpers if useful. NO cross-tenant (12.15). NO new dep.

Files (§6): NEW `backend/services/flywheel/skill_roi.py` (pure fns), NEW
`backend/api/v1/routes/flywheel.py` (read-only `GET /flywheel/skills/roi`), NEW
`backend/tests/unit/test_skill_roi.py`. Register the new router in the app. Def-of-done §10: ROI
correlations + ranking + confidence + explainability + read endpoint + golden test, ≥90% on the
engine, suite green, commit. No PR (phase-end).

---

## 12.14 — Tenant Isolation Framework

Implement Phase 12.14 — Tenant Isolation Framework. Add a `tenants` table + request-scoped
`TenantContext` + a CENTRAL repository guard so no query runs unscoped, across SQLite + Chroma + KG +
outcomes + the 12.10 `signals` table. Produces ADR-008.

PRECONDITION: depends on 12.2 (SHIPPED). This is the foundation 12.10 deferred to. **Read the
roadmap "Privacy boundary" section first — binding.** This segment is FOUNDATIONAL + BROAD + a
security boundary → this is where an ADR is genuinely warranted (ADR-008): one-DB + enforced
`tenant_id` + local-profile model (no authn). Write the ADR.

Read first (STOP once you have the table list + acceptance): (1)
`docs/superpowers/plans/2026-06-22-phase-12-14-tenant-isolation.md` (goals §2, acceptance §4, design
§5, file plan §6, TDD §7) + the roadmap privacy-boundary section. (2) `docs/04_DATABASE_SCHEMA.md` —
every tenant-owned table that needs a `tenant_id` column. (3) `backend/repositories/base.py` (the
central choke point for the filter) + `backend/rag/chroma_client.py` (metadata `where`, already
composes `doc_type` from 12.6). (4) `backend/models/signal.py` (the nullable `tenant_id` to flip).

Order fixed: brainstorm (confirm: one DB + `tenant_id` FK everywhere + central guard, NOT per-DB
files — spec §3) → **ADR-008 (write it)** → TDD (guard test + isolation/leak test FIRST per §7) →
migration+model+backfill → central repo filter + TenantContext → Chroma where → route wiring → verify.

Traps: (1) **The central guard is the whole point** — a missing tenant filter must be a HARD ERROR,
not a silent full-table read (test: an unscoped query RAISES, doesn't leak). Enforce in
`repositories/base.py`, not per-query discipline. (2) **`tenant_id` nullable→backfill→NOT NULL in ONE
revision** (spec §5 ponytail): add nullable, backfill all existing rows + 12.10 `signals` to a
`default` tenant, then `ALTER`/recreate NOT NULL + FK — SQLite needs batch_alter / table-rebuild for
NOT NULL+FK; use alembic `batch_alter_table`. (3) **ALEMBIC ISOLATION** — test up→head AND down→base
with `ACOS_DB_PATH=$(mktemp -u).db`; the migration is broad, a real-DB mistake is costly. (4)
**create_all parity** — add `tenant_id` to the SQLAlchemy models too (not just the migration) or
create_all builds the old schema; new `tenants` model registered in `models/__init__.py`. (5)
**Chroma leak** — every read/write carries the tenant `where`; a cross-tenant query returns nothing
(test). (6) **Existing tests** — they now need a tenant; update the conftest to seed/inject a
`default` tenant so the suite stays green without rewriting every test.

Reuse: `repositories/base.py` filter choke point; Chroma `where` composition from 12.6; conftest
fixtures. context7 batch: SQLAlchemy 2.0 multi-tenant + `batch_alter_table`, Chroma metadata filter.

Rules+: run `security-review` (isolation IS the security boundary — review for leak paths) +
`requesting-code-review`. Files §6 (model, tenancy.py, tenant_id on owned models, repo filter, chroma
edits, route TenantContext, migration, ADR-008, 2 tests). Def-of-done §10: enforced isolation across
SQLite/Chroma/KG/outcomes + default-tenant backfill + leak tests green + ADR-008 + ≥90% on the
isolation layer + security review clean + suite green + commit.

---

## 12.12 — Resume Strategy Intelligence Layer

Implement Phase 12.12 — Resume Strategy Intelligence Layer. Compose signals (12.10) + skill ROI
(12.11) into per-tenant resume structure + ATS strategy recommendations, grounded in the tenant's own
evidence with confidence levels. This is the recommendation layer the user sees; it ADVISES the
existing resume engine, doesn't replace it.

PRECONDITION: depends on 12.10 + 12.11 (confirm both shipped). No new table per §6 — read-side
compose. If 12.14 has landed, take a real `TenantContext`; else thread `tenant_id: str | None`.

Read first (STOP at acceptance + the resume-engine input shape): (1)
`docs/superpowers/plans/2026-06-22-phase-12-12-resume-strategy-intelligence.md` (§2 goals, §3
non-goals, §4 acceptance, §5 design — the `StrategyRecommendation` dataclass, §7 TDD). (2)
`backend/services/flywheel/skill_roi.py` (12.11 ROI ranks you consume). (3) SKIM
`backend/services/resume/` + `backend/services/ats/scorer.py` — the input shape your hints must match
(acceptance §4: "no schema mismatch") + `evidence_selector` for evidence links.

Order fixed: brainstorm (confirm: compose ROI + rollups + JD analysis into a dataclass; no new resume
generation) → ADR? skip (no architecture decision; consumes existing layers) → TDD (rich-data →
confident recs; sparse → generic+weak_inference; unknown industry → flagged, per §7) → implement → verify.

Traps: (1) **No hallucinated best-practices** — every recommendation cites the tenant's own
evidence + confidence; sparse data degrades to `weak_inference`, NEVER fabricates a "best practice"
(acceptance §4, CLAUDE.md non-negotiable #1). (2) **Industry taxonomy** — recs keyed by a DEFINED
industry set; unknown industry → generic + flagged, not a crash or a guess. (3) **Resume-engine
integration** — output must drop into existing resume/ATS inputs as OPTIONAL hints (don't break the
unhinted path; the resume engine works with no strategy). (4) tenant scoping as above.

Reuse: 12.11 ROI, 12.10 rollups/explain, resume `evidence_selector`, ATS `keyword_extractor`. NO new
export formats, NO global/cross-tenant (12.15). Plugin §8: `skill-creator` only if the industry
taxonomy needs nodes. Files §6: NEW `backend/services/flywheel/strategy.py`, EDIT
`routes/flywheel.py` (+`GET /flywheel/strategy`), EDIT `services/resume/*` (accept optional strategy
hints), NEW `test_strategy_intelligence.py`. Def-of-done §10: personalized structure + ATS strategy +
confidence + evidence + resume-engine integration + taxonomy-keyed, ≥90%, suite green, commit.

---

## 12.13 — Adaptive Prompt Evolution

Implement Phase 12.13 — Adaptive Prompt Evolution. Let prompts evolve from success signals as
VERSIONED, REVERSIBLE, APPROVAL-GATED proposals — never a silent live mutation. Touches generation
quality, so the Phase 11 rule is hard: versioned + reversible + explainable.

PRECONDITION: depends on 12.10 + 12.11; BUILDS ON Phase 11.2 prompt locking/versioning (SHIPPED —
`PromptVersion` model + prompt loader exist). Confirm the 11.2 prompt-version table/loader API before
coding. EXTEND it (add candidate versions + active pointer + transitions); do NOT replace the locking
mechanism (§3).

Read first (STOP at acceptance + the prompt-version store API): (1)
`docs/superpowers/plans/2026-06-22-phase-12-13-adaptive-prompt-evolution.md` (§2 goals, §3 non-goals,
§4 acceptance, §5 design — `propose/trial/promote/rollback`, §7 TDD). (2)
`backend/models/optimization.py` (`PromptVersion`, `ABExperiment`, `ABVariant`) +
`backend/services/prompt_loader.py` (active-version resolution). (3) SKIM
`backend/services/optimization/` (`ab_testing.py`, `guardrails.py`, `prompt_evolver.py`, `applier.py`
— REUSE the A/B + guardrails; they already exist from Phase 8/11).

Order fixed: brainstorm (confirm: proposal = new version row + rationale linked to signals;
promotion = flip active pointer + audit; reuse optimization/ A/B) → ADR? skip unless the
version-transition model is genuinely new (it extends 11.2 — likely no ADR; if the active-pointer +
audit design is novel, a short ADR is OK — don't manufacture one) → TDD (propose→new version,
incumbent unchanged; rollback restores; promote blocked w/o approval; promote w/ approval flips +
audit — per §7) → implement → verify.

Traps: (1) **No autonomous prod mutation** — promotion REQUIRES explicit approval (`approved_by`); a
promote call without approval is rejected (test). The incumbent active prompt is NEVER overwritten —
candidates are new rows. (2) **Reversible** — one-call `rollback(prompt_id)` restores the prior
active version; audit row for every transition (who/what/why, extends 11.2 observability). (3)
**Explainable** — proposal rationale links the SIGNALS that triggered it (reuse 12.10 explain /
rollup); no unexplained prompt change. (4) **O(1) active resolution** — active-prompt lookup stays a
pointer read; no per-request regression (trials run off-hot-path/opt-in).

Reuse: 11.2 `PromptVersion` + loader; optimization/ `ab_testing` + `guardrails` + `prompt_evolver`.
Plugin §8: `ralph-loop` (trial loop) + `requesting-code-review` (quality-affecting). Files §6: NEW
`backend/services/flywheel/prompt_evolution.py`, EDIT prompt-version store/loader (candidate +
active pointer), EDIT `optimization/*` (wire prompt A/B), EDIT a route (propose/trial/promote/rollback,
approval-gated), NEW `test_prompt_evolution.py` + `test_prompt_ab_promotion.py`. Def-of-done §10:
versioned reversible signal-driven proposals + guardrailed A/B + approval-gated promotion + one-call
rollback + full audit, ≥90%, existing prompt tests green, code-review, commit.

---

## 12.15 — Privacy-Preserving Global Pattern + ROI Aggregation

Implement Phase 12.15 — Privacy-Preserving Global Pattern + ROI Aggregation. Mine
STRUCTURAL/STATISTICAL patterns across tenants (section orderings, keyword-density bands, skill
clusters, global skill-ROI per industry) as ABSTRACTIONS ONLY, behind a k-anonymity emission gate.
Produces ADR-009.

PRECONDITION: depends on 12.11 + 12.14 (BOTH must be shipped — needs ≥2 isolated tenants + per-tenant
ROI). **Read the roadmap "Privacy boundary" section first — BINDING.** If 12.14 isn't shipped, STOP
and record the blocker — this segment cannot meet acceptance without real tenant isolation. This is a
privacy boundary → ADR-009 is warranted (write it).

Read first (STOP at acceptance + the privacy boundary): (1)
`docs/superpowers/plans/2026-06-22-phase-12-15-global-aggregation.md` (§2 goals, §3 STRICT non-goals,
§4 acceptance, §5 design — `global_patterns.py` + `anonymization.gate()`, §7 TDD) + the roadmap
privacy-boundary section. (2) `backend/services/flywheel/skill_roi.py` (12.11 — per-tenant ROI you
aggregate, reading ROLLUPS not rows). (3) `backend/services/tenancy.py` (12.14 — how tenants are
enumerated/scoped).

Order fixed: brainstorm (confirm: read per-tenant rollups/ROI NEVER rows; gate every emission through
k-anonymity + field allowlist; content-free global store) → **ADR-009 (write it)** → TDD
(`test_anonymization_gate` suppress <k + reject disallowed fields; `test_no_reidentification` scan
every artifact for raw text/embeddings/tenant ids; `test_global_aggregation` multi-tenant rankings —
FIRST, per §7) → migration+model (content-free `global_patterns`) → aggregator + gate → verify.

Traps: (1) **k-anonymity gate is the deliverable** — any pattern backed by < k=5 contributing tenants
is DROPPED (test asserts suppression). The gate is a hard filter, not advisory. (2) **No
re-identification** — a test scans every global artifact: zero raw text, zero embeddings, zero tenant
ids; only allowlisted abstract fields may be emitted. (3) **NO NETWORK** — operates on local tenants
only, nothing leaves the machine (CLAUDE.md local-only). (4) **Global never overrides local** — 12.12
consumes global patterns as SUGGESTIONS, re-personalized + confidence-tagged. (5) **No global prompt
auto-promotion** — global can propose (12.13) but promotion stays local + approval-gated. (6)
**ALEMBIC ISOLATION** (`ACOS_DB_PATH` temp db) + create_all parity for the new table. (7) ponytail:
k-anonymity gate first; add DP noise only if a re-id test defeats it.

Reuse: 12.11 ROI, 12.14 tenancy enumeration, 12.10 rollups. Plugin §8: `security-review` (privacy
boundary IS the deliverable) + `serena` reasoning. Files §6: NEW `global_patterns.py`,
`anonymization.py`, `models/global_pattern.py` (+register), migration, EDIT `strategy.py` (consume
global, re-personalized), EDIT `routes/flywheel.py` (global ROI read), ADR-009, 3 tests. Def-of-done
§10: cross-tenant extractor + global ROI + k-anonymity gate + no-reid test green + feeds 12.12
re-personalized + ADR-009 + no network, ≥90%, security review clean, suite green, commit.

---

## 12.16 — Phase 12 Close-out (Docs, Audit, ADRs, Review)

Run Phase 12.16 — Phase 12 Close-out. Verification + documentation ONLY — no new features. Verify the
whole phase holds: budgets met, privacy boundary intact, docs current, ADRs ratified,
security/privacy reviewed. Then the branch is ready to merge to `main`.

PRECONDITION: depends on ALL shipped Phase 12 segments. Close out ONLY what landed — spikes 12.8/12.9
were research/defer; do NOT force deferred work to ship to "complete" the phase. First action:
enumerate what actually shipped (git log on the branch + MEMORY.md) and what was deferred + why.

Read first (STOP once you have the shipped/deferred map + doc list): (1)
`docs/superpowers/plans/2026-06-22-phase-12-16-closeout.md` (§2 goals, §4 acceptance, §6 doc list).
(2) `docs/PERFORMANCE_LOG.md` + the 12.0 bench harness (re-run benches, confirm every ceiling held).
(3) MEMORY.md `project-phase12-plan` (the shipped-state ledger).

Order: NOT freestyle — this is a checklist. brainstorm? no (verification task). No new code → no TDD
(but the suite must be green + coverage met). (1) Final perf audit: re-run 12.0 benches, confirm
budgets, log final numbers in PERFORMANCE_LOG. (2) Privacy/security: end-to-end leak audit of 12.14
isolation + 12.15 anonymization; run `security-review` (clean, no HIGH/MED). (3) Docs: update
ROADMAP, ARCHITECTURE_OVERVIEW, 02_TECHNICAL_ARCHITECTURE, 06_RAG_DESIGN, 04_DATABASE_SCHEMA (new
tables: signals, tenants, global_patterns, + any others), USER_GUIDE, TROUBLESHOOTING, README,
OPTIMIZATION_SYSTEM, INDEX. (4) ADRs: ratify ADR-008, ADR-009, + any 12.9 spike ADRs. (5) Roadmap
segment map annotated shipped/deferred + why.

Traps: (1) **verification-before-completion** — every "done"/"budget held" claim backed by a REAL
re-run command + number, never asserted unseen (paste the bench table + coverage report). (2) **Close
out only what shipped** — deferrals are documented as deferred, not silently dropped or force-shipped.
(3) **Schema doc must list every new table** — signals (12.10), tenants (12.14), global_patterns
(12.15), prompt-evolution rows (12.13). (4) ponytail/caveman pass: confirm the phase didn't accrete
unrequested complexity.

Plugin §8: `verification-before-completion`, `security-review` (full tenant+privacy pass),
`code-review` (phase-level on the merged branch), `caveman`/`ponytail`. Files §6: docs edits +
roadmap annotations + ADR ratification — no new services. Def-of-done §10: budgets verified, privacy
audited clean, docs + ADRs current, roadmap annotated, suite green → **Phase 12 ready to merge to
`main`** (this is where the phase PR opens).
```
