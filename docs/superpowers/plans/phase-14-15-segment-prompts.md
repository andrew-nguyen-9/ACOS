# Phase 14–15 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. Each is self-contained and token-budgeted.
**8 segments** (3 Phase-14 + 4 Phase-15 + close-out) — deliberately coarse: Phases 12–13 lost time to
too-small segments + restarts. Map + reconciliation: `phase-14-15-roadmap.md`.
Phase ends at **14-15.8 (close-out)** — no .9+.

## Recommended order (dependency-correct)

```
14.1 versioning & reproducibility   (foundation; semver + determinism + DMG release-verify)
14.2 observability & drift          ← 14.1   ┐ parallel after 14.1
14.3 security audit + ADR-013       ← 14.1   ┘ (plugin/ecosystem/cloud DEFER)
15.1 autonomy ADR-012 + job rank    ← 14 stable   (write the boundary BEFORE any agent surface)
15.2 application suggestion         ← 15.1   ┐ parallel after 15.1
15.3 interview sim deepening        ← 15.1   ┘
15.4 daily briefing + goals         ← 15.1, 15.2   (off-hot-path orchestrator)
14-15.8 close-out                   ← all shipped
```

## Session-wide invariants (true for ALL — stated once, assume in every prompt)

- **Branch:** `feat/phase-14-15-hardening-and-agent` (off `main` — Phase 13 merged, `b77e143`). Each
  segment = one commit on this branch. **PR deferred to 14-15.8.** Git Attribution: NO Claude/Anthropic
  in commits/PRs/branches (CLAUDE.md).
- **Rules in force (CLAUDE.md non-negotiables):** no hallucination — every user-facing figure
  (success-prob, interview-prob, ROI, drift) traces to a source record + confidence per ADR-006
  (`verified`/`strong_inference`/`weak_inference`); **estimates are labeled estimates, never bare
  numbers**; read `docs/` before coding; **`context7` for framework APIs** (Tauri v2, FastAPI,
  SQLAlchemy 2.0, Chroma, React 18, framer-motion) — never from memory. TDD: failing test FIRST,
  ≥90% on new code, existing suite stays green. Ponytail: rung 1 first (does a single-user local app
  need this? — re-justify each new file/table/service); descriptive stats before any model. Caveman:
  terse prose; code/commits/security normal.
- **Token-efficiency (every segment):** RTK on shell ops. ONE `context7` batch up front (not per-file).
  ONE read pass — the segment spec + ONLY the files you'll touch; STOP reading once you have the
  contract + acceptance. Do NOT re-read shipped Phase 9/11/12/13 plans (state is in `MEMORY.md` + the
  schema/route docs + the services on disk). Land small: ADR-if-real → failing test → thin code →
  green → verify with real output → commit.
- **Backend test seam (unchanged since 12):** `backend/tests/conftest.py` `_SyncSessionBridge` runs
  `session.run_sync(fn)` against in-memory SQLite (StaticPool, FK ON), default tenant seeded.
  `test_session` for unit/integration; `client` (TestClient) for routes. **ALEMBIC ISOLATION:** any
  migration runs ONLY with `ACOS_DB_PATH=$(mktemp -u).db` (env.py ignores `DATABASE_URL`); verify
  up→head AND down→base on a temp db. **create_all parity:** new model → register in
  `backend/models/__init__.py`; non-ORM tables need an `after_create` hook (FTS5 precedent, 12.7).
- **Frontend invariants:** stack = Tauri v2 + React 18 + TS + Tailwind + framer-motion (Phase 11
  design system, P3 tokens, `lib/capability.ts` tiers, `webgl/clock.ts` pause authority). Reuse
  `services/api.ts` `apiFetch<T>` + `ApiError` — do NOT add a new HTTP client. Reuse the 13.0
  primitives (`components/ui/ConfidenceBadge.tsx`, `DormantEmptyState.tsx`) for confidence/empty
  states. Vitest unit; Playwright e2e for golden paths. **Perf gate (BLOCKING where there's
  interaction):** 60fps, 0 long-tasks, CLS ≈ 0, entry ≤ 80.8 kB gz, Off tier usable — verify live via
  chrome-devtools, paste the result. CSP unchanged.
- **Shipped surface you build on (verify shapes from the file before wiring — don't assume fields):**
  - **Strategy engines (Phase 9), `backend/services/strategy/`:** `application_strategy.py`
    (`ApplicationStrategyEngine`, `PrioritizeRequest`), `role_fit_scorer.py`, `skill_gap_forecaster.py`,
    `career_path_simulator.py`, `resume_strategy_selector.py`, `outcome_learner.py`, `corpus_scraper.py`.
    Routes in `backend/api/v1/routes/strategy.py` (Phase 9; `PrioritizeRequest`, `RoleFitRequest`,
    `ResumeStrategyRequest`, …). Models in `backend/models/strategy.py`.
  - **Flywheel (Phase 12), `backend/services/flywheel/`:** `skill_roi.py`, `strategy.py`,
    `global_patterns.py`, `prompt_evolution.py`, `evolution_loop.py` (13.6 off-hot-path watcher),
    `feedback.py`, `anonymization.py`. Routes in `routes/flywheel.py`.
  - **Optimization (Phase 8/12), `backend/services/optimization/`:** `ab_testing.py`, `guardrails.py`,
    `loop.py`, `recommender.py`, `applier.py`, `evaluator.py`, `prompt_evolver.py`. Routes in
    `routes/optimization.py`. Prompt-version substrate in `backend/models/optimization.py`
    (`PromptVersion`, `ABExperiment`).
  - **Observability:** `backend/observability.py` (`TimingMiddleware`, `X-Response-Time` + perf log),
    `backend/services/observability/`, `routes/observability.py`, `docs/PERFORMANCE_LOG.md`.
  - **Interview / Q&A:** `backend/services/questions/generator.py`, `routes/questions.py`,
    `frontend/src/pages/InterviewPrepPage.tsx` (3-seat panel + `CadenceMeter`), `services/knowledge_graph/`.
  - **CRM / applications:** `backend/models/application.py` (`Application` + `ApplicationTimeline`,
    `status` draft/…), `routes/application.py`, `frontend/src/pages/ApplicationsPage.tsx`.
  - **Resume / CL / ATS:** `services/resume/`, `services/cover_letter/` (CL `tone` param, 11.9),
    `services/ats/`; pages `ResumePage.tsx`, `CoverLetterPage.tsx`, `AtsPage.tsx`.
  - **Packaging (13):** `frontend/src-tauri/tauri.conf.json` (bundle/signing/updater), `lib.rs`
    (sidecar spawn — **NOT Ollama**; Ollama is external per `MODEL_SETUP.md`), `docs/PACKAGING.md`.
  - **Backup/integrity (11.4):** `backend/services/backup/`, `backend/integrity.py`, `routes/backup.py`,
    `routes/maintenance.py`.

---

## 14.1 — Versioning & Reproducibility Spine

Implement Phase 14.1 — one coherent **versioning + reproducibility** story across the app, plus the
**DMG release-verification** owed from 13.8. Consolidates brief items 3 (versioning) + 8 (deterministic
seeded generation, reproducible ATS). Foundation for 14.2/14.3.

PRECONDITION: Phase 13 merged. The pieces exist scattered — Alembic migrations, `PromptVersion` (prompt
lock, ADR-010), model keep_alive/build (12.5), updater + prompt rollback (13.9). This segment *unifies
the surface*, it does NOT rebuild any of them.

Read first (STOP once you have the version sources + the generation seed path): (1) `phase-14-15-roadmap.md`
(reconciliation table). (2) `backend/config.py` + `frontend/src-tauri/tauri.conf.json` (where the app
semantic version lives — single source of truth) + `pyproject.toml`. (3) the resume generation entry
(`backend/services/resume/` generator) + `backend/services/ollama_client.py` (the `seed`/`options` path —
is generation seedable today?). (4) `backend/services/ats/` scorer (is ATS scoring already
deterministic given fixed input?). (5) `routes/health.py` (where a version/build endpoint fits) +
`backend/models/optimization.py` `PromptVersion` + `backend/services/__init__.py`-level model-version
tracking (12.5).

Order: brainstorm (confirm: a single `GET /health/version` returning app semver + model name/version +
active prompt-version ids + migration head; AND a determinism guarantee — generation accepts/threads a
`seed` so a fixed (seed, inputs, prompt-version, model) tuple is reproducible, and ATS scoring is
asserted reproducible) → ADR? skip (no new boundary; consolidation) → TDD (backend: version endpoint
returns all four fields; **same-seed resume gen is byte-stable** across two runs with a stubbed/seeded
LLM; **ATS score reproducible** for fixed input; migration up→head→down→base on temp db) → implement →
verify (paste pytest + the two reproducibility tests + DMG steps below).

Traps: (1) **Reproducibility needs the whole tuple** — "deterministic when seeded" means seed + inputs +
prompt-version + model are all pinned; the test fixes all four (don't claim determinism while the
prompt-version floats). (2) **LLM seed reality** — confirm via `context7`/Ollama whether `seed` in
`options` gives reproducible output for the pinned model; if not fully deterministic, the guarantee is
scoped to "seed-pinned + greedy decode" and **documented honestly** (don't overclaim — CLAUDE.md #1).
(3) **One version source** — app semver has ONE home (don't duplicate between `tauri.conf.json` and
Python); the endpoint reads it, doesn't redefine it. (4) **DMG release-verify (owed from 13.8):** on a
real machine, install the signed DMG, launch, first-run wizard fires (13.7), core path works; **record
cold-start ms** — that number is the 12.9.3/Nuitka reopen gate (paste it; if it >400ms, that's a
backlog-reopen note, NOT a build here).

Files: NEW/EDIT `routes/health.py` (version endpoint), thread `seed` through the resume generator +
`ollama_client` if missing, NEW `backend/tests/` reproducibility tests, `docs/PACKAGING.md` +
`docs/PERFORMANCE_LOG.md` (DMG verify + cold-start), maybe a `VERSIONING.md` note. Def-of-done: version
endpoint (app+model+prompt+migration) + seeded-reproducible generation + reproducible ATS (tests pasted)
+ DMG release-verified with cold-start recorded, migration up/down green, suite green, commit.

---

## 14.2 — Observability & Drift Dashboard (local-first)

Implement Phase 14.2 — surface system health + add the three **drift metrics** the brief names (ATS
accuracy drift, resume success rate, embedding quality drift) over the existing observability, with a
local-only dashboard. Brief item 4. **No external telemetry** (kept).

PRECONDITION: 14.1 (version endpoint — drift is reported against a version). `backend/observability.py`
(latency) + `services/observability/` + `routes/observability.py` + `PERFORMANCE_LOG.md` exist. The
**outcome signals** drift is computed from already exist: `backend/services/flywheel/feedback.py`
(rollups), `models/outcome.py`, `models/signal.py`, `models/metric.py`.

Read first (STOP at the observability route shape + the signal sources): (1) roadmap. (2)
`backend/observability.py` + `backend/services/observability/` + `routes/observability.py` (what's
already exposed). (3) `backend/services/flywheel/feedback.py` + `models/outcome.py`/`signal.py`/`metric.py`
(the raw signals: application outcomes → success rate; ATS scores over time → accuracy drift; embedding
norms/recall over time → embedding drift). (4) `frontend/src/pages/LearningPage.tsx` (analytics IA — the
dashboard slots near it) + the 13.0 `services/flywheel.ts` pattern.

Order: brainstorm (confirm: an **off-hot-path** drift computation — a rollup/service method, NOT
per-request — over existing signals, exposed via observability routes; a FE dashboard surfacing latency
+ the 3 drifts as trend cards with confidence + low-n handling) → ADR? skip (no new boundary; local-only
reaffirmed) → TDD (backend: drift methods compute correctly on a fixed signal fixture; low-n → suppressed
not fabricated; FE: cards render trends, low-n shows `weak_inference`/dormant) → implement → verify
(pytest + live perf gate on the dashboard page).

Traps: (1) **Off-hot-path** — drift is computed on a schedule/rollup (reuse the 13.6 `evolution_loop`/
maintenance scheduler seam — do NOT add a new scheduler); assert no per-request latency added. (2)
**Drift needs a baseline** — "drift" = change vs a recorded baseline (tie to 14.1's version); without a
baseline there's nothing to drift from, so seed/record one. (3) **Low-n honesty** — thin data → no
confident drift number (ADR-006); reuse `DormantEmptyState`. (4) **No external telemetry** — everything
stays local; do NOT add any outbound call (the only net channel is 13.9's updater). (5) ponytail:
descriptive trend (rolling mean/delta) before any forecasting model.

Files: NEW drift methods in `backend/services/observability/`, EDIT `routes/observability.py`, EDIT
`services/*.ts` + a dashboard section (EDIT `LearningPage.tsx` or NEW `components/observability/DriftDashboard.tsx`),
vitest + pytest + e2e. Def-of-done: 3 drift metrics computed off-hot-path against a versioned baseline +
local dashboard with confidence/low-n handling, no external telemetry, perf gate passed (paste), suites
green, commit.

---

## 14.3 — Security Audit + Optional Encrypted Storage + Ecosystem/Plugin Reconciliation (ADR-013)

Implement Phase 14.3 — a consolidated **security pass**, an **optional** encrypted-local-storage knob,
and the **ADR-013** that records the deliberate deferral of the runtime-plugin/cloud/API-exposure brief
items. Brief items 5 + 6 + 7 + 2. Mostly audit + ADR (cheap); the only new code is the optional storage
knob. **`security-review` mandatory.**

PRECONDITION: 14.1. Security primitives exist: `backend/ingestion/security.py` (allowlist+size+malformed
catch), the 13.8 asset:// path chokepoint (`lib.rs` `resolve_asset_path`), no-eval policy. The
"plugin system" in this repo is the **dev workflow** (`docs/07_PLUGIN_ORCHESTRATION.md`), not a runtime
engine.

Read first (STOP at the security surfaces + the plugin-doc): (1) roadmap reconciliation rows 2/5/6/7. (2)
`backend/ingestion/security.py` + `backend/ingestion/parsers/` (the validated upload path) +
`frontend/src-tauri/src/lib.rs` `resolve_asset_path` (the canonicalize+starts_with chokepoint). (3)
`backend/database.py` + `config.py` (where an at-rest encryption option would wrap SQLite — SQLCipher or
app-layer field encryption; **decide via `context7`**, don't pick from memory). (4)
`docs/07_PLUGIN_ORCHESTRATION.md` + `docs/SECURITY_DEPENDENCIES.md` + ADR-001/008 (the local-first +
network boundary this ADR-013 leans on).

Order: brainstorm (confirm two threads: (A) **audit** the existing ingest/path/exec surfaces against a
checklist + run `security-review`, fix any HIGH/MED; (B) **optional** encrypted storage — OFF by default,
opt-in, with an honest threat-model note (local-disk-theft only; not a multi-user boundary); (C) write
**ADR-013** deferring runtime-plugin-engine + cloud-sync + API-exposure + 3rd-party/job-board net
integrations, and formalizing the existing service-module + dev-plugin contract) → **ADR-013 (write it)**
→ TDD (encrypted-storage round-trip: write→encrypted-at-rest→read-back; OFF path unchanged/byte-identical;
ingestion security tests still green) → implement → `security-review` → verify.

Traps: (1) **Encrypted storage is OPTIONAL + honest** — default OFF; the threat model it actually
addresses is local disk theft, NOT multi-user/network (don't overclaim — CLAUDE.md). Reproducibility
(14.1) + backup (11.4) must still work with it ON. (2) **No new unguarded surface** — the audit must
confirm no path bypasses `ingestion/security.py` / `resolve_asset_path`; no `eval`/`exec` on parsed
content. (3) **ADR-013 is a deferral, justified** — ponytail rung 1: a single-user local app does not
need a runtime plugin engine or cloud; record WHY + the reopen condition (don't silently drop the brief
items — document them deferred). (4) **No new dependency for crypto unless `context7` says it's the right
one** — prefer a maintained, reviewed option; field-level over a custom cipher.

Files: NEW `docs/adr/ADR-013-*.md`, optional encryption wrapper in `backend/database.py`/`config.py` +
tests, `docs/SECURITY_DEPENDENCIES.md` audit note, EDIT `docs/07_PLUGIN_ORCHESTRATION.md` (formalize the
contract). Def-of-done: security audit clean (security-review, no HIGH/MED) + optional encrypted storage
(opt-in, round-trip tested, OFF path unchanged) + ADR-013 (plugin/cloud/API deferral recorded) + suites
green, commit.

---

## 15.1 — Controlled-Autonomy Framework (ADR-012) + Job Discovery / Prioritization Surface

Implement Phase 15.1 — write the **autonomy boundary (ADR-012) FIRST**, then surface the existing Phase-9
`ApplicationStrategyEngine` as a ranked, explained, success-probability **job-prioritization** view from
pasted/saved JDs. Brief item 1 + the autonomy boundary. This ADR gates every later 15.x agent surface.

PRECONDITION: Phase 14 stable. The engine exists: `backend/services/strategy/application_strategy.py`
(`ApplicationStrategyEngine`, `PrioritizeRequest`), `role_fit_scorer.py`, `skill_gap_forecaster.py`;
route `routes/strategy.py` (`PrioritizeRequest`). **You surface + orchestrate; you do NOT rebuild the
engine.** ADR-010 (propose-never-promote) is the precedent pattern.

Read first (STOP at the prioritize contract + a page IA to extend): (1) roadmap (ADR-012 stub +
reconciliation). (2) `backend/services/strategy/application_strategy.py` + `role_fit_scorer.py` +
`backend/models/strategy.py` (`PrioritizeRequest` + the ranked-output + success-prob + explain shape).
(3) `routes/strategy.py` (the existing prioritize route — confirm transport; JD is large → POST body,
not query param, like 13.2's strategy). (4) `frontend/src/pages/ApplicationsPage.tsx` (CRM — where a
"prioritize" view fits; reuse `Application` + saved JDs) + the 13.0 `ConfidenceBadge`. (5) ADR-010 (the
never-act pattern to mirror).

Order: brainstorm (confirm: **ADR-012** defines MAY rank/recommend/generate/simulate vs MAY NOT
submit/contact/mutate-external/act-without-approval, enforced by *the absence of any outbound-action code
path*; THEN a job-prioritization surface — paste/select JDs → ranked rows with success-prob + reasoning +
skill-gap, each confidence-tagged, sortable but server-ranked) → **ADR-012 (write it FIRST)** → TDD
(backend route test if the route gains behavior; FE: ranked render follows server order; success-prob
shows confidence + evidence, never bare; **a test asserts no submit/outreach action exists on the
surface**) → implement → verify (vitest + live perf gate).

Traps: (1) **ADR-012 before any agent UI** — the boundary is the deliverable; later segments cite it. (2)
**No outbound action path** — the prioritization view ranks + explains only; there is NO "apply"/"contact"
button that hits an external system (a test asserts this — the whole boundary, like 13.6's
never-promotes). (3) **Estimates are labeled** — success-probability carries confidence + the evidence it
came from; low-n → `weak_inference`, excluded from "top pick" emphasis (ADR-006). (4) **Server-ranked,
deterministic** — render the engine's order; don't re-rank client-side. (5) ponytail: reuse
ApplicationsPage + saved JDs; add a JobsPage only if the CRM page can't host it cohesively.

Files: NEW `docs/adr/ADR-012-*.md`, EDIT `routes/strategy.py` only if behavior is added, EDIT
`services/*.ts` + `ApplicationsPage.tsx` (+ maybe `components/strategy/JobPrioritization.tsx`), vitest +
e2e + backend test if route changes. Def-of-done: ADR-012 (controlled-autonomy boundary) + ranked
explainable confidence-tagged job-prioritization surface from existing engine + no-outbound-action test +
perf gate passed, suites green, commit.

---

## 15.2 — Application Suggestion Engine (Apply / Skip / Tailor)

Implement Phase 15.2 — a per-application **recommendation**: Apply / Skip / Tailor-First, with the
suggested resume version, cover-letter style, and interview-probability — surfacing existing engines.
Brief item 3. **HARD RULE: no automatic submission** (ADR-012; enforced + tested).

PRECONDITION: 15.1 (ADR-012 + the prioritization surface). Engines exist: `resume_strategy_selector.py`
(resume version), cover-letter `tone` (11.9), `role_fit_scorer.py` (interview probability),
`skill_gap_forecaster.py`. **Surface, don't rebuild.**

Read first (STOP at the selector outputs + ApplicationsPage detail view): (1) roadmap + ADR-012. (2)
`backend/services/strategy/resume_strategy_selector.py` + `role_fit_scorer.py` (the recommendation +
interview-prob shapes). (3) `routes/strategy.py` (existing endpoints; add a thin one only if a combined
"suggestion" shape isn't exposed). (4) `frontend/src/pages/ApplicationsPage.tsx` (the per-application
detail — where the suggestion card slots) + `services/cover_letter` tone param.

Order: brainstorm (confirm: per-application suggestion card — Apply/Skip/Tailor recommendation +
recommended resume version + CL tone + interview-prob, each confidence-tagged + explained; the action
buttons are **internal-only** (open the tailor flow, mark status) — never an external submit) → ADR? skip
(consumes ADR-012) → TDD (backend: combined-suggestion shape if a thin route is added; FE: card renders
all four with confidence; Apply opens the internal tailor/track flow, NOT an external POST; **a test
asserts no auto-submit code path**) → implement → verify (vitest + live perf gate).

Traps: (1) **No auto-submit, ever** — Apply marks status / opens the internal compose flow; there is no
code that submits to a job board (test it — ADR-012). (2) **Tailor-First is the safe default on low
fit** — when role-fit/confidence is low, the recommendation is "Tailor First," not "Apply" (mirror the
engine; don't over-encourage). (3) **Every recommendation is explained** — Apply/Skip/Tailor cites the
fit/gap evidence + confidence; no bare verdict (ADR-006). (4) reuse the resume/CL flows already wired in
ResumePage/CoverLetterPage — don't fork generation.

Files: EDIT `routes/strategy.py` (thin combined-suggestion route only if needed) + `services/*.ts` +
`ApplicationsPage.tsx` (+ maybe `components/strategy/ApplicationSuggestion.tsx`), vitest + e2e + backend
test if route added. Def-of-done: per-application Apply/Skip/Tailor suggestion + resume-version + CL-tone
+ interview-prob, all confidence-tagged + explained, **no-auto-submit test green**, internal-only
actions, perf gate passed, suites green, commit.

---

## 15.3 — Interview Simulation Deepening

Implement Phase 15.3 — deepen the existing interview prep into a **simulation**: recruiter-behavior
modeling, follow-up question generation, and KG-grounded answer evaluation. Brief item 4. **Extend
`InterviewPrepPage.tsx` + `services/questions/generator.py`** — they already do per-application questions +
a 3-seat panel + cadence.

PRECONDITION: 15.1 (ADR-012). Exists: `backend/services/questions/generator.py`, `routes/questions.py`,
`InterviewPrepPage.tsx` (panel + `CadenceMeter`), `backend/services/knowledge_graph/` (the graph answers
are evaluated against). **Deepen, don't replace.**

Read first (STOP at the generator contract + the KG query surface): (1) roadmap. (2)
`backend/services/questions/generator.py` + `routes/questions.py` (current Q generation — where follow-ups
+ recruiter-persona thread in). (3) `backend/services/knowledge_graph/` (how to query the graph to score
an answer's grounding/coverage). (4) `frontend/src/pages/InterviewPrepPage.tsx` (the panel/Q flow + where
an answer-eval + follow-up affordance fits) + `services/learning.ts`/`applications.ts` it already uses.

Order: brainstorm (confirm: (a) recruiter-behavior persona threaded into question generation (tone/depth
per panel seat); (b) follow-up questions generated from the user's answer; (c) answer evaluation grounded
in the KG — coverage of expected evidence, confidence-tagged, with the supporting node ids) → ADR? skip
(consumes ADR-012; simulation is generate/simulate, allowed) → TDD (backend: follow-up generation given an
answer; KG eval returns coverage + the evidence ids it matched, low coverage → honest low score; FE:
answer → eval renders with confidence + follow-up appears) → implement → verify (vitest + perf gate;
interview-panel audio/cadence must still pass the 11.9 perf gate).

Traps: (1) **Answer eval cites the graph** — a score is backed by which KG nodes the answer did/didn't
cover (ADR-006); never a bare "7/10". (2) **Simulation is generate-only** — no external action; the
recruiter is simulated locally (ADR-012). (3) **Reuse the 11.9 audio/panel** — extend `InterviewPrepPage`,
don't add a second audio context or GL canvas; the 11.9 spatial-panel perf gate still applies. (4)
ponytail: follow-ups + persona ride the existing generator prompt(s) (versioned YAML, `backend/prompts/`)
— don't add a new generation engine.

Files: EDIT `backend/services/questions/generator.py` (+ persona/follow-up), maybe a KG-eval method in
`services/knowledge_graph/`, EDIT `routes/questions.py`, prompt YAML under `backend/prompts/questions/`,
EDIT `InterviewPrepPage.tsx`, vitest + pytest + e2e. Def-of-done: recruiter-persona questions + answer
follow-ups + KG-grounded confidence-tagged answer eval, simulation stays generate-only, 11.9 panel perf
gate still passes (paste), suites green, commit.

---

## 15.4 — Daily Career Briefing + Goal Alignment

Implement Phase 15.4 — an **off-hot-path** orchestrator that composes a daily briefing (jobs to apply to,
skill gaps, resume adjustments, ATS opportunities, follow-ups needed) aligned to career goals, surfaced on
the Dashboard. Brief items 2 + 5. Composes 15.1/15.2 + existing engines; schedules like 13.6.

PRECONDITION: 15.1 + 15.2 (the prioritization + suggestion surfaces it composes). Exists:
`career_path_simulator.py` (goal/trajectory), `application_strategy.py`, `skill_gap_forecaster.py`,
flywheel `feedback.py`, ATS, `models/application.py` (follow-up state via `ApplicationTimeline`/`status`),
the 13.6 `evolution_loop.py`/maintenance scheduler seam. `Dashboard.tsx` is the surface.

Read first (STOP at the compose inputs + the scheduler seam): (1) roadmap. (2) the four engines above (the
methods that yield: ranked jobs (15.1), skill gaps, resume/ATS opportunities, follow-ups due) +
`career_path_simulator.py` (the goals to align against). (3) the 13.6 `evolution_loop.py` /
`routes/maintenance.py` scheduler seam (reuse — do NOT add a new scheduler). (4) `frontend/src/pages/Dashboard.tsx`
+ the 13.0 `services/flywheel.ts`/`ConfidenceBadge` (the briefing card surface).

Order: brainstorm (confirm: a `briefing` service that, off-hot-path, composes the five sections from the
existing engines + aligns each recommendation to the tracked career goal; a `GET /briefing` read surface;
a Dashboard briefing card; **schedule via the existing seam / `hookify`**, not a new scheduler; the whole
thing is recommend-only per ADR-012) → ADR? skip (consumes ADR-012; orchestration, no new boundary) → TDD
(backend: briefing composes all five sections from fixed fixtures; goal-misaligned recommendations are
flagged/down-ranked; empty inputs → honest empty sections not fabrications; FE: card renders sections with
confidence + dormant handling) → implement → verify (pytest + live perf gate).

Traps: (1) **Off-hot-path** — the briefing is computed on a schedule/on-demand rollup (reuse the 13.6
seam); it must not add per-request latency to any generation path (assert it). (2) **Goal alignment is
real, not decorative** — each recommendation is checked against the `career_path_simulator` goal and
flagged when misaligned (don't just list everything). (3) **Recommend-only** — the briefing suggests
("apply to X", "follow up on Y"); it never acts (ADR-012); follow-ups are surfaced, not sent. (4) **Honest
empties** — a new user with no data gets labeled-empty sections (DormantEmptyState), never invented jobs/
gaps (ADR-006). (5) ponytail: compose existing engine outputs; write only the orchestrator + the briefing
read + the card — no new ranking/scoring.

Files: NEW `backend/services/briefing/` (orchestrator) or a method on an existing service, NEW
`GET /briefing` route, schedule hook on the existing seam, EDIT `services/*.ts` + `Dashboard.tsx` (+ maybe
`components/briefing/DailyBriefing.tsx`), vitest + pytest + e2e. Def-of-done: off-hot-path daily briefing
(jobs/gaps/resume/ATS/follow-ups) aligned to goals + Dashboard surface + scheduled via existing seam +
recommend-only (boundary test) + honest empties, perf gate passed (paste), suites green, commit.

---

## 14-15.8 — Phase 14–15 Close-out (Docs, ADRs, Review, Merge)

Run Phase 14-15.8 — verification + documentation ONLY, no new features. Confirm the phase holds: gates
met, autonomy boundary enforced, optional-encryption honest, docs current, ADRs ratified,
security/privacy reviewed → branch ready to merge to `main`.

PRECONDITION: all shipped 14.x/15.x segments. First action: enumerate what actually shipped (git log on
the branch + `MEMORY.md`) and what stayed deferred + why (runtime-plugin engine, cloud, API-exposure,
Win/Linux pkg, authn, the VOID 12.9 backlog).

Read first (STOP once you have the shipped/deferred map + the doc list): (1) `phase-14-15-roadmap.md`
(reconciliation + deferred tables). (2) `docs/PERFORMANCE_LOG.md` + the 14.1 cold-start / 14.2 drift
baselines. (3) `MEMORY.md` `project-phase14*/15*` (the shipped-state ledger).

Order: a checklist, not freestyle. (1) **Final perf/quality audit:** confirm FE perf gates held across the
new surfaces (job-rank, suggestion, interview-sim, briefing dashboard) + the 14.2 drift/14.1 cold-start
numbers logged. (2) **Security/privacy + autonomy:** end-to-end review — the **no-outbound-action**
boundary holds across 15.1/15.2/15.4 (no submit/contact/external-mutate path); optional-encryption claims
are honest; run `security-review` (clean, no HIGH/MED). (3) **Docs:** update `08_ROADMAP` (Phase 14–15
outcomes block + numbering caveat), `ARCHITECTURE_OVERVIEW`, `02_TECHNICAL_ARCHITECTURE`, `USER_GUIDE`
(job prioritization / suggestions / interview sim / daily briefing / versioning), `TROUBLESHOOTING`,
`README`, `INDEX` (mark 14–15 shipped), `PACKAGING`/`MODEL_SETUP` (DMG verify). (4) **ADRs:** ratify
ADR-012 (controlled autonomy) + ADR-013 (plugin/ecosystem/cloud deferral). (5) **Roadmap annotation:**
segment map marked shipped/deferred + reasons.

Traps: (1) **verification-before-completion** — every "done"/"gate held" backed by a real re-run + number;
never asserted unseen. (2) **Close out only what shipped** — deferrals documented as deferred, not
silently dropped (runtime-plugin, cloud, API, Win/Linux, authn). (3) **The autonomy boundary is the
headline** — docs + ADR-012 must state plainly: ACOS recommends, never acts; no auto-apply, no recruiter
outreach. (4) ponytail/caveman pass: confirm the phase didn't accrete unrequested complexity (no runtime
plugin engine crept in; no cloud).

Plugin: `verification-before-completion`, `security-review` (autonomy + encryption pass), `code-review`
(phase-level), `claude-md-management` (docs structure), `caveman`/`ponytail`. Files: docs edits + roadmap
annotations + ADR-012/013 ratification — no new services. Def-of-done: gates verified, autonomy + security
boundaries audited clean, docs + ADRs current, roadmap annotated, suite green → **Phase 14–15 ready to
merge to `main`** (the phase PR opens here).
