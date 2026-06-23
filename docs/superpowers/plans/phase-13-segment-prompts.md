# Phase 13 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. Each is self-contained and token-budgeted.
Phase ends at **13.11 (close-out)** — no 13.12. Map + rationale: `phase-13-roadmap.md`.

## Recommended order (dependency-correct)

```
13.0 FE data layer       (foundation; no route exists to break)
13.1 skill-ROI dashboard ← 13.0
13.4 prompt-evolution UI ← 13.0   (build the human GATE before the automation that feeds it)
13.6 automation loop     ← 13.4   ADR-010
13.2 strategy hints      ← 13.0   ┐ parallel after 13.0/13.1
13.3 global suggestions  ← 13.1   ┘
13.5 onboarding+coldstart← 13.0   (extend FirstRunWizard)
13.7 first-run model-pull← 13.5   ┐ packaging track, after surfaced UI stable
13.8 macOS DMG           ←         │
13.9 auto-update         ← 13.8   ┘ ADR-011 (network boundary)
13.10 verification debt  ← all backend stable
13.11 close-out          ← all shipped
```

## Session-wide invariants (true for ALL — stated once, assume in every prompt)

- **Branch:** `feat/phase-13-surfacing-onboarding-packaging` (off `main` after Phase 12 merges; else off
  `feat/phase-12-...` HEAD `aafea4c`). Each segment = one commit on this branch. **PR deferred to 13.11.**
  Git Attribution: NO Claude/Anthropic in commits/PRs/branches.
- **Rules in force (CLAUDE.md non-negotiables):** no hallucination — every user-facing figure traces to a
  source record + confidence level per ADR-006 (`verified`/`strong_inference`/`weak_inference`); read `docs/`
  before coding; **`context7` for framework APIs** (Tauri v2, FastAPI, SQLAlchemy 2.0, Chroma, React 18,
  framer-motion) — never code them from memory. TDD: failing test FIRST, ≥90% on new code, existing suite
  stays green. Ponytail: descriptive stats before any model; re-justify each new file (rung 1: does a
  single-user local app need this?). Caveman: terse prose; code/commits/security normal.
- **Token-efficiency (every segment):** RTK on shell ops. ONE `context7` batch up front (not per-file). ONE
  read pass — the segment spec + ONLY the files you'll touch; STOP reading once you have the contract +
  acceptance. Do NOT re-read shipped Phase 11/12 plans (state is in MEMORY.md + the schema/route docs). Land
  small: ADR-if-real → failing test → thin code → green → verify with real output → commit.
- **Backend test seam (unchanged from 12):** `backend/tests/conftest.py` `_SyncSessionBridge` runs
  `session.run_sync(fn)` against in-memory SQLite (StaticPool, FK ON), default tenant seeded. `test_session`
  for unit/integration; `client` (TestClient) for routes. **ALEMBIC ISOLATION:** any migration runs ONLY with
  `ACOS_DB_PATH=$(mktemp -u).db` (env.py ignores `DATABASE_URL`); verify up→head AND down→base on a temp db.
  **create_all parity:** new model → register in `backend/models/__init__.py`; non-ORM tables need an
  `after_create` hook. *(Phase 13 is mostly read-side + frontend; new tables are unlikely — if a segment adds
  one, these apply.)*
- **Frontend invariants:** stack = Tauri v2 + React 18 + TS + Tailwind + framer-motion (Phase 11 design
  system, P3 tokens, `lib/capability.ts` tiers, `webgl/clock.ts` pause authority). Reuse `services/api.ts`
  `apiFetch<T>` + `ApiError` — do NOT add a new HTTP client (ponytail). Vitest for unit; Playwright e2e for
  golden paths. **Perf gate (BLOCKING where there's interaction):** 60fps, 0 long-tasks, CLS ≈ 0, entry ≤
  80.8 kB gz, Off tier usable — verify live via chrome-devtools, paste the result. CSP unchanged (except 13.9).
- **Backend surface you build on (Phase 12, all shipped):** routes in `backend/api/v1/routes/flywheel.py` —
  `GET /flywheel/skills/roi`, `GET /flywheel/strategy`, `GET /flywheel/global/roi`,
  `POST /flywheel/prompt/{propose,trial,promote,rollback}`. Services in `backend/services/flywheel/`:
  `skill_roi.py`, `strategy.py`, `global_patterns.py`, `prompt_evolution.py`, `feedback.py`,
  `anonymization.py`. **Confirm each route's response shape from the route file before wiring a component to
  it** — don't assume field names.

---

## 13.0 — Frontend Flywheel Data Layer + Confidence Primitives

Implement Phase 13.0 — the typed client + shared UI primitives every surfacing segment (13.1–13.5) reuses.
Foundation only; ships no user-visible feature by itself.

PRECONDITION: none (no route is mutated). The flywheel routes already exist (Phase 12) and are unconsumed.

Read first (STOP once you have the route shapes + the design-system entry points): (1) `phase-13-roadmap.md`
(theme table + gates). (2) `backend/api/v1/routes/flywheel.py` — the EXACT response shapes of all four GET/POST
families (field names, confidence fields, the k<5 empty case for global). (3) `frontend/src/services/api.ts`
(`apiFetch`/`ApiError` you reuse) + one sibling like `services/learning.ts` for the module shape. (4)
`frontend/src/lib/capability.ts` + `components/ui/` (GlassCard etc.) for the design vocabulary.

Order: brainstorm (confirm: a `services/flywheel.ts` of typed fns over `apiFetch` + ONE `ConfidenceBadge`
+ ONE `DormantEmptyState`; NO new client, NO state-manager) → ADR? skip (no boundary) → TDD (vitest: client
parses each shape incl. k<5 empty; badge renders the 3 levels; type round-trip) → implement → verify (tsc +
vitest output pasted).

Traps: (1) **Mirror the real response types** — generate TS types from the route file's actual fields, not
guesses; a field-name drift is the bug. (2) **Confidence is first-class** — `ConfidenceBadge` renders exactly
ADR-006's three levels with distinct affordances; `weak_inference` visibly distinct (it gates user trust).
(3) **k<5 dormancy** — global ROI returns empty/suppressed under k-anonymity (ADR-009); the client + empty-state
treat "suppressed" as a normal state, not an error. (4) ponytail: no caching layer until a measured re-fetch
problem; `apiFetch` direct is fine.

Files: NEW `frontend/src/services/flywheel.ts`, NEW `frontend/src/components/shared/ConfidenceBadge.tsx`,
NEW `frontend/src/components/shared/DormantEmptyState.tsx`, NEW `frontend/src/types/flywheel.ts`, tests
alongside. Def-of-done: typed client for all four route families + 3-level badge + dormant empty-state, tsc
clean, vitest green ≥90% on new code, commit. No route changes, no new page.

---

## 13.1 — Skill-ROI Dashboard

Implement Phase 13.1 — surface `GET /flywheel/skills/roi` as a ranked, explainable, confidence-tagged view.
**Extend `LearningPage.tsx`** (it already exists and owns learning/analytics IA) — do NOT add a new page.

PRECONDITION: 13.0 (client + ConfidenceBadge). Confirm the roi route's ranked output + per-item explain refs.

Read first (STOP at the route shape + LearningPage's section structure): (1)
`docs/superpowers/plans/phase-13-roadmap.md`. (2) `frontend/src/services/flywheel.ts` (13.0). (3)
`frontend/src/pages/LearningPage.tsx` — where a new ROI section slots in, existing motion/section patterns.
(4) `backend/api/v1/routes/flywheel.py` skill_roi response (the ranked list + contributing-signal ids).

Order: brainstorm (confirm: a ROI section IN LearningPage — ranked rows, each with n, confidence badge, and an
expandable "why" listing contributing signal/outcome ids from the route's explain refs) → ADR skip → TDD
(vitest: renders ranks; low-n row shows `weak_inference` + is not in a "recommended" emphasis; explain expands)
→ implement → verify (vitest + live perf gate on the page).

Traps: (1) **No confident ROI on thin data** — low-n surfaces `weak_inference` and is excluded from any
"recommended" emphasis (mirror the backend's exclusion; don't re-rank client-side). (2) **Explainability is
visible** — every ROI row can show its contributing ids; no orphan number. (3) **Determinism** — render order
follows the server ranking exactly (stable). (4) perf: virtualize only if the list is long (reuse Phase 11
`@tanstack/react-virtual`); otherwise plain list (ponytail).

Files: EDIT `frontend/src/pages/LearningPage.tsx` (+ROI section), maybe NEW
`components/learning/SkillRoiSection.tsx` if LearningPage is already large, vitest + e2e `learning-roi`.
Def-of-done: ranked + confidence + explainable ROI section live, low-n correctly de-emphasized, perf gate
passed (paste), vitest green, commit.

---

## 13.2 — Resume-Editor Strategy Hints

Implement Phase 13.2 — surface `GET /flywheel/strategy` as inline, OPTIONAL, non-blocking hints in the resume
editor. **Extend `ResumePage.tsx`.** Hints advise; the editor works fully with hints off or absent.

PRECONDITION: 13.0. 12.12 `strategy.py` returns per-tenant structure/ATS recommendations with confidence +
evidence + industry key. Confirm the route's recommendation shape + the "unknown industry → flagged" case.

Read first (STOP at the strategy shape + the resume editor's structure): (1) roadmap. (2)
`services/flywheel.ts`. (3) `frontend/src/pages/ResumePage.tsx` + `components/resume/` (where a hint affordance
fits — reuse the 11.8 `BulletXRay` glass-popover pattern if apt). (4) `routes/flywheel.py` strategy response.

Order: brainstorm (confirm: hints render as dismissible, confidence-tagged affordances tied to resume
sections; sparse data → generic + `weak_inference`; unknown industry → flagged chip, never a fabricated "best
practice") → ADR skip → TDD (vitest: rich data → confident hint; sparse → weak + generic; unknown industry →
flagged; editor renders identically with hints disabled) → implement → verify.

Traps: (1) **Non-blocking** — the unhinted resume path must be byte-identical; hints are additive overlay, not
a gate. (2) **No hallucinated best-practice** — every hint cites the tenant's own evidence + confidence
(CLAUDE.md #1); sparse → degrade to weak, never invent. (3) **Industry flagging** — unknown industry shows a
flag, not a guess. (4) reuse the existing popover/specular patterns; no new overlay engine.

Files: EDIT `ResumePage.tsx` + maybe `components/resume/StrategyHints.tsx`, vitest + e2e `resume-strategy`.
Def-of-done: optional confidence-tagged hints wired, unhinted path unchanged, perf gate passed, vitest green,
commit.

---

## 13.3 — Global-Pattern Suggestions Surface

Implement Phase 13.3 — surface `GET /flywheel/global/roi` as re-personalized, confidence-tagged suggestions.
**Extend `LearningPage.tsx`** (alongside 13.1's ROI section). Honors ADR-009: global never overrides local.

PRECONDITION: 13.1 (LearningPage ROI section + client). With < 5 local profiles the route is k-anonymity
suppressed → this surface is **dormant by design** today; build the dormant empty-state path as the primary
demoable state.

Read first (STOP at the global route shape + ADR-009 §5): (1) roadmap. (2) `services/flywheel.ts` +
`components/shared/DormantEmptyState.tsx` (13.0). (3) `routes/flywheel.py` global/roi response (+ the
suppressed shape). (4) `docs/adr/ADR-009-privacy-preserving-aggregation.md` §1/§5 (read-aggregates-not-rows;
global = suggestion only, re-personalized + confidence-tagged).

Order: brainstorm (confirm: render global patterns as SUGGESTIONS re-framed against the tenant's own evidence
+ confidence; under k<5 show the dormant empty-state explaining "needs ≥5 profiles," not an error) → ADR skip
(consumes ADR-009) → TDD (vitest: k<5 → dormant state; k≥5 mock → suggestions render with `tenant_count` +
confidence, framed as suggestions not directives) → implement → verify.

Traps: (1) **Global ≠ override** — copy + affordances frame these as suggestions to consider, re-personalized;
never "you must." (2) **Dormant is normal** — k<5 suppression is the expected current state; the empty-state is
informative, not a failure. (3) **No re-identification leakage** — render only the allowlisted abstract fields
the route returns (`tenant_count` is a count, never ids); don't infer or display membership.

Files: EDIT `LearningPage.tsx` (+global suggestions section), vitest + e2e `learning-global`. Def-of-done:
suggestions surface with re-personalization + confidence + working dormant state, no re-id leakage, perf gate
passed, vitest green, commit.

---

## 13.4 — Prompt-Evolution Review/Approval UI

Implement Phase 13.4 — the human-in-the-loop gate for prompt evolution: list candidates, view rationale +
A/B trial results, **approve-to-promote** or rollback, with an audit trail. **Extend `OptimizationPage.tsx`.**
This is the destination 13.6's automation feeds — build it FIRST.

PRECONDITION: 13.0. 12.13 `prompt_evolution.py` + the four POST routes (propose/trial/promote/rollback) exist;
promotion is approval-gated server-side (`approved_by` required). Confirm each POST's request/response + how a
candidate's rationale links its triggering signals (12.10 explain).

Read first (STOP at the four route contracts + OptimizationPage structure): (1) roadmap. (2) `routes/flywheel.py`
prompt/* routes. (3) `frontend/src/pages/OptimizationPage.tsx` + `services/optimization.ts`. (4) SKIM
`backend/services/flywheel/prompt_evolution.py` for the candidate/active/audit fields the UI displays.

Order: brainstorm (confirm: a review queue of candidates with rationale + signal links + trial deltas; an
explicit Approve action that sends `approved_by`; a one-click Rollback; an audit list — all over existing
routes, no new endpoint) → ADR skip → TDD (vitest: promote disabled until an approver is set; approve sends
`approved_by`; rollback calls rollback; audit renders transitions) → implement → verify.

Traps: (1) **Approval is a deliberate human act** — promote is impossible without an explicit approver in the
UI (mirror the server gate; never auto-fill). (2) **Incumbent visibility** — the active prompt is clearly
marked; candidates are clearly "not live." (3) **Explainable** — each candidate shows the signals that
triggered it (reuse the route's rationale/explain refs); no unexplained proposal. (4) **Reversible** — rollback
is one action and visibly restores the prior active version. (5) destructive-action confirm on promote/rollback.

Files: EDIT `OptimizationPage.tsx` (+ review/approval section), maybe `components/optimization/PromptReview.tsx`,
vitest + e2e `optimization-prompt-review`. Def-of-done: candidate queue + rationale/signal links + approval-gated
promote + one-click rollback + audit view, perf gate passed, vitest green, commit.

---

## 13.5 — Onboarding Doc-Upload + Cold-Start Surfacing

Implement Phase 13.5 — let a new user build their profile by uploading documents, and surface the cold-start
intelligence. **Extend the existing `FirstRunWizard.tsx`** (it already does welcome→ollama→profile→done; the
gap is the *document-upload → graph-build → Career-Voice* step inside `profile`).

PRECONDITION: 13.0. Backend cold-start (12.3) + `writing_profiles` + skill/experience-graph ingestion already
exist — confirm the ingestion/build endpoints (resume/cover-letter/job-history upload → skill graph +
experience graph + ATS baseline + writing-style profile) before wiring. If an endpoint is missing, add a THIN
route over existing services; don't build a new ingestion engine.

Read first (STOP at the ingestion endpoints + the wizard's `profile` step): (1) roadmap. (2)
`frontend/src/pages/FirstRunWizard.tsx` (the `Step` machine + `apiFetch` usage). (3) the resume/document
ingestion routes (`backend/api/v1/routes/` — find the upload + build endpoints) + `services/resume`,
writing-profile builder. (4) ADR-006 (cold-start/synthetic inference must be labeled).

Order: brainstorm (confirm: extend the wizard with a document-upload sub-step that posts files → triggers the
existing build → shows the resulting skill/experience/ATS/Career-Voice summary with confidence; synthetic
inferences CLEARLY LABELED; whole step is skippable) → ADR? skip (no boundary; reuses ingestion) → TDD (vitest:
upload posts to the build endpoint; cold-start summary renders with labeled synthetic items; skip path leaves
the wizard completable) → implement → verify. **Split to 13.5.x only if** upload + graph-build + Career-Voice
surfacing exceed one cohesive commit.

Traps: (1) **Synthetic labeling** — cold-start/template-inferred items are visibly `weak_inference` and labeled
synthetic (CLAUDE.md #1); never presented as verified user history. (2) **File ingestion security** — reuse the
existing validated upload path (allowlist, size limit, malformed-file catch); do NOT add a new unguarded upload.
(3) **Skippable** — a user with nothing to upload still completes onboarding (cold-start templates fill in,
labeled). (4) **Career-Voice = surfacing, not a new model** — display the writing-style profile the backend
already derives; don't invent new scoring.

Files: EDIT `FirstRunWizard.tsx` (+upload/cold-start sub-step), maybe `components/onboarding/*`, possibly a THIN
backend route if the build trigger isn't exposed, vitest + e2e `onboarding`. Def-of-done: upload → graph/ATS/
Career-Voice build surfaced with labeled confidence, secure reused upload path, skippable, perf gate passed,
suite green, commit.

---

## 13.6 — Prompt-Evolution Automation Loop

Implement Phase 13.6 — an off-hot-path job that watches success signals and **auto-proposes** prompt candidates
into the 13.4 review queue. It NEVER promotes. Produces **ADR-010**.

PRECONDITION: 13.4 (the human approval destination must exist) + 12.13 (`prompt_evolution.py` propose/trial +
optimization guardrails). This adds autonomy → ADR-010 is warranted (write it). Plugin: `ralph-loop` for the
loop scaffold; `requesting-code-review` + `security-review` (autonomy boundary).

Read first (STOP at the propose/trial API + guardrails): (1) roadmap + the ADR-010 stub in
`phase-13-roadmap.md`. (2) `backend/services/flywheel/prompt_evolution.py` (propose/trial — you call these, you
do NOT reimplement). (3) `backend/services/optimization/guardrails.py` + `ab_testing.py` (reuse the existing
guardrails + A/B). (4) `backend/services/flywheel/feedback.py` (the signals the watcher reads via `rollup`).

Order: brainstorm (confirm: a scheduled/off-hot-path watcher reads rollups, and when a signal threshold is met
calls the EXISTING `propose` + guardrailed `trial`, writing candidates to the review queue; promotion path is
untouched) → **ADR-010 (write it)** → TDD (failing tests FIRST: threshold met → exactly one proposal queued
with linked signals; promotion is never called by the loop; guardrail veto suppresses a proposal; idempotent —
no duplicate proposals for the same signal window) → implement → verify (paste coverage + the "never promotes"
test).

Traps: (1) **NEVER auto-promotes** — the loop has no promote path; a test asserts promote is never invoked
(this is the whole boundary). (2) **Off-hot-path** — the watcher must not regress request latency; it runs on a
schedule/background, not in the generation path (no per-request cost — assert active-prompt resolution stays an
O(1) pointer read). (3) **Guardrailed** — every auto-proposal passes the existing optimization guardrails; a
veto drops it. (4) **Explainable + idempotent** — each proposal links its triggering signals (reuse explain)
and the same signal window doesn't spawn duplicates. (5) ponytail: reuse `ralph-loop` + existing guardrails;
write only the watcher + threshold + queue-write glue.

Files: NEW `backend/services/flywheel/evolution_loop.py` (watcher/threshold/glue), the schedule hook (reuse
the Phase 11 maintenance/scheduler seam if present — don't add a new scheduler), `docs/adr/ADR-010-*.md`, NEW
`backend/tests/unit/test_evolution_loop.py`. Def-of-done: signal-driven auto-proposer feeding 13.4 + never
promotes + guardrailed + idempotent + off-hot-path + ADR-010 + ≥90% on the loop + code-review + security-review
clean + suite green + commit.

---

## 13.7 — First-Run Model-Pull Progress + DMG First-Run Hook

Implement Phase 13.7 — finish the first-run experience for a packaged app: live Ollama model-pull progress and
the hook that triggers the wizard on first launch of the DMG. **Extend the existing `FirstRunWizard.tsx`** (it
already checks `/health/ollama` + lets the user pick a model — the gap is *pulling* a missing model with
progress, and triggering first-run in the packaged app).

PRECONDITION: 13.5 (onboarding step). Packaging context for 13.8. Confirm whether the backend exposes a
model-pull/progress endpoint; if not, add a THIN streaming route over Ollama's pull (reuse the 12.4 SSE
helper).

Read first (STOP at the ollama-pull path + the first-run trigger): (1) roadmap. (2) `FirstRunWizard.tsx`
(`ollama` step: `OllamaStatus`, `missing_models`, model pick). (3) the health/ollama route + any existing
ollama-admin route + the 12.4 SSE helper (`backend/.../sse.py`). (4) `settings.ts` `completeOnboarding` (the
first-run-done flag).

Order: brainstorm (confirm: when a model is missing, offer pull with streamed progress; persist first-run-done;
no auto-pull without consent) → ADR skip → TDD (vitest: missing model → pull control shown; progress renders
from the stream; completion sets the done flag) → implement → verify.

Traps: (1) **Consent before pull** — a multi-GB model download is user-initiated, never silent. (2) **Degraded
path** — if Ollama is unreachable, the wizard still completes into a clearly-degraded mode (don't hard-block
the app). (3) **Reuse SSE** — stream progress via the existing 12.4 disconnect-safe helper; no new streaming
primitive. (4) packaged-only behaviors (first-run trigger) are honestly marked as verified only in the DMG
(manual check), like the 11.8 native-haptics note.

Files: EDIT `FirstRunWizard.tsx`, maybe a THIN `routes` ollama-pull (SSE), vitest + e2e. Def-of-done:
consent-gated model-pull with live progress + degraded fallback + first-run-done persisted, vitest green,
commit. (DMG trigger verified in 13.8.)

---

## 13.8 — macOS DMG Packaging

Implement Phase 13.8 — produce a distributable macOS DMG via `tauri build`, bundling the Python sidecar +
frontend, with a signed artifact. This reclaims the displaced M5 packaging milestone (macOS first).

PRECONDITION: surfaced UI (13.1–13.5) + first-run (13.7) stable. `context7` for Tauri v2 bundling + macOS
signing/notarization — do NOT configure `tauri.conf.json` bundle/signing from memory. Trap-1 from 12.5 is
binding: **`lib.rs` spawns the Python sidecar, NOT Ollama** — the DMG bundles the app + sidecar; Ollama is a
documented external prerequisite (`MODEL_SETUP.md`), not bundled.

Read first (STOP at the bundle config + sidecar packaging): (1) roadmap. (2) `src-tauri/tauri.conf.json` +
`src-tauri/src/lib.rs` (sidecar spawn, asset:// scheme, CSP). (3) the sidecar build (PyInstaller — the locked
packager; Nuitka stays DEFER per backlog unless cold-start >400ms fires). (4) `docs/MODEL_SETUP.md` (the
external-Ollama contract the DMG documents).

Order: brainstorm (confirm: `tauri build` → DMG bundling app + PyInstaller sidecar; Ollama external + documented;
signing config) → ADR skip (packaging mechanics, no new architecture; ADR-011 is 13.9's, not this) → build →
**verify on the release machine: install the DMG, launch, first-run wizard fires (13.7), core path works** →
record cold-start ms (feeds 13.10 / backlog 12.9.3 condition).

Traps: (1) **Sidecar path resolution** — the packaged sidecar path differs from dev; verify the spawned path
resolves inside the bundle (the classic packaging break). (2) **External Ollama, honestly** — the DMG does not
bundle Ollama; first-run + `MODEL_SETUP.md` make the prerequisite explicit (no hallucinated "it just works").
(3) **Signing/notarization** — unsigned DMG warns on launch; configure signing (or document the gatekeeper
step honestly if no cert). (4) **Measure cold-start** on the real release machine — that number is the
12.9.3/Nuitka reopen gate; record it, don't assume.
└ **13.8.1 Windows · 13.8.2 Linux** — deferred (roadmap backlog); build only if explicitly requested. Each is
its own sub-segment with its own bundle/signing config.

Files: EDIT `src-tauri/tauri.conf.json` (bundle/signing), build scripts under `scripts/`, `docs/` packaging
note. Def-of-done: installable signed macOS DMG, launches, first-run fires, core path verified on the release
machine (paste the steps + cold-start ms), commit.

---

## 13.9 — Background Auto-Update + Release Notes

Implement Phase 13.9 — true background auto-update for the packaged app, plus release-notes surfacing.
Produces **ADR-011**. ⚠️ **This deliberately breaks CLAUDE.md local-only/no-network** — by explicit user
decision. `security-review` is MANDATORY.

PRECONDITION: 13.8 (a signed DMG to update from/to). `context7` for the Tauri v2 updater (signature
verification, update manifest, endpoints) — configure from current docs, not memory.

Read first (STOP at the updater contract + the security requirements): (1) roadmap + the ADR-011 stub. (2)
Tauri v2 updater docs (via context7): signed update artifacts, public-key verification, the update endpoint/
manifest. (3) `src-tauri/tauri.conf.json` CSP + `docs/adr/ADR-008` §Forward-looking (the network/IDOR note this
crosses). (4) `src-tauri/src/lib.rs` (where the updater wires in).

Order: brainstorm (confirm the scope of the network break: updater fetches a signed manifest + artifact over
TLS; signature verified before apply; release notes shown; NO telemetry beyond the version check) → **ADR-011
(write it FIRST — this is the boundary decision)** → implement updater config → **`security-review`** → verify
(a signed update applies; a tampered/unsigned artifact is REJECTED).

Traps: (1) **Signature verification before apply** — an update is applied ONLY if its signature verifies
against the bundled public key; a tampered artifact is rejected (test/verify this — it's the security crux).
(2) **TLS + minimal surface** — the only network call is the update check/fetch over TLS; no analytics, no
identity, no `X-Tenant-Id` on the wire (ADR-008 §Forward-looking stays non-live). (3) **CSP** — add ONLY the
update origin to CSP; document the single deliberate relaxation. (4) **Honest boundary** — ADR-011 states
plainly that this overrides the local-only default for the update channel only; user-visible, not silent
surveillance. (5) **Rollback/safety** — a failed update must not brick the app (Tauri updater atomicity);
confirm the failure path.

Files: EDIT `src-tauri/tauri.conf.json` (updater + CSP), `src-tauri/src/lib.rs` (updater wiring),
`docs/adr/ADR-011-*.md`, release-notes surface (FE), signing keys handled out-of-repo (no secrets committed —
CLAUDE.md). Def-of-done: signed background auto-update (verify-before-apply + tamper rejected) + release notes
+ ADR-011 + single documented CSP/network relaxation + security-review clean + no committed secrets + commit.

---

## 13.10 — Verification Debt + Optimization Re-Baseline

Run Phase 13.10 — pay down the 12.16 verification debt and re-check the deferred-optimization backlog with real
numbers. Mostly harness/test work; new product code is minimal.

PRECONDITION: backend stable (13.1–13.6 landed). `OLLAMA_LIVE=1` for the live benches. This is the "Both"
runtime half of token-efficiency: re-baseline the 12.0 harness and check each reopen condition — they stay
VOID unless a number fires.

Read first (STOP once you have the harness entry points + the reopen conditions): (1) roadmap + the deferred
table. (2) `docs/optimization/deferred-optimization-backlog.md` (the exact reopen conditions + numbers). (3)
the 12.0 bench harness + `docs/PERFORMANCE_LOG.md`. (4) the RAG retrieval path (`backend/rag/`,
`EvidenceSelector`) for the golden-set harness.

Order: NOT freestyle — a checklist. (a) **Live-Ollama bench runner (8a):** a runnable gate that re-runs TTFT +
structured-output benches against live Ollama; record numbers in PERFORMANCE_LOG. (b) **Scored golden-set
retrieval harness (8b):** a fixed query→expected-evidence set with a scored metric (recall@k / nDCG) so
"retrieval correctness" is a measured baseline, not asserted via filtering tests; freeze the baseline. (c)
**12.0 re-baseline → reopen check (theme 7):** run the harness on real payloads; for each backlog item
(msgpack/FAISS/Nuitka/pinned-mem) record whether its condition fired — paste the number; if none fired, they
stay VOID (do NOT adopt). (d) **Global-aggregation demo (8c):** a synthetic ≥5-profile fixture that exercises
the k-anonymity path end-to-end so 12.15/13.3 are demoable (fixture only — does NOT create real profiles).

Traps: (1) **Real numbers only** — every claim is a pasted command + number (verification-before-completion);
no asserted-green benches. (2) **Reopen needs a number** — a backlog item reopens ONLY if its measured
condition fires; otherwise it stays VOID (Ponytail rung 1, burden on adopt). (3) **Synthetic ≥5 fixture is
test-only** — it must not write real tenants or leak into the dev DB (ALEMBIC ISOLATION; temp/in-memory). (4)
**Golden-set is frozen** — baseline scores are committed so future retrieval changes regress against a real
number.

Files: NEW `scripts/perf/` live-bench runner, NEW `backend/tests/` golden-set retrieval harness + fixtures,
PERFORMANCE_LOG updates, a re-baseline note in the backlog doc. Def-of-done: live-Ollama bench gate + scored
golden-set baseline + re-baseline table with per-item reopen verdicts (numbers pasted) + ≥5-profile demo
fixture, suite green, commit. (Any item whose condition fired → its OWN brainstorm+ADR+plan, NOT here.)

---

## 13.11 — Phase 13 Close-out (Docs, ADRs, Review, Merge)

Run Phase 13.11 — verification + documentation ONLY, no new features. Confirm the phase holds: gates met, the
network boundary documented, docs current, ADRs ratified, security/privacy reviewed → branch ready to merge to
`main`.

PRECONDITION: all shipped Phase 13 segments. First action: enumerate what actually shipped (git log on the
branch + MEMORY.md) and what stayed deferred + why (multi-profile UI, Chroma read-filter, authn, Win/Linux pkg,
the VOID backlog items).

Read first (STOP once you have the shipped/deferred map + the doc list): (1)
`docs/superpowers/plans/phase-13-roadmap.md` (theme table + deferred table). (2) `docs/PERFORMANCE_LOG.md` +
the 13.10 results. (3) MEMORY.md `project-phase13-*` (the shipped-state ledger).

Order: a checklist, not freestyle. (1) **Final perf/quality audit:** confirm FE perf gates held across the new
surfaces + the 13.10 numbers logged. (2) **Security/privacy:** end-to-end review of the 13.9 update boundary
(signed-update verified, single CSP relaxation, no secrets) + confirm 13.6 never-promote holds; run
`security-review` (clean, no HIGH/MED). (3) **Docs:** update ROADMAP (Phase 13 outcomes block),
ARCHITECTURE_OVERVIEW, 02_TECHNICAL_ARCHITECTURE, USER_GUIDE (onboarding + ROI/strategy surfaces + update),
TROUBLESHOOTING, README, FRONTEND_DESIGN, INDEX, MODEL_SETUP (packaging/prereq). (4) **ADRs:** ratify ADR-010 +
ADR-011; re-record the ADR-008 §Forward-looking authn boundary as still-deferred + WHY (now that auto-update
adds network). (5) **Roadmap annotation:** segment map marked shipped/deferred + reasons.

Traps: (1) **verification-before-completion** — every "done"/"gate held" claim backed by a real re-run +
number; never asserted unseen. (2) **Close out only what shipped** — deferrals documented as deferred, not
silently dropped. (3) **The network boundary is now real** — docs + ADR-011 must state plainly that the app is
no longer strictly no-network (update channel only); ADR-008's authn note is now load-bearing — say so. (4)
ponytail/caveman pass: confirm the phase didn't accrete unrequested complexity.

Plugin: `verification-before-completion`, `security-review` (full update-boundary + autonomy pass),
`code-review` (phase-level), `claude-md-management` (docs structure), `caveman`/`ponytail`. Files: docs edits +
roadmap annotations + ADR-010/011 ratification — no new services. Def-of-done: gates verified, update + autonomy
boundaries audited clean, docs + ADRs current, roadmap annotated, suite green → **Phase 13 ready to merge to
`main`** (the phase PR opens here).
```
