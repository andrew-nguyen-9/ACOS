# Phase 14–15 — Hardening / Deployment Readiness · Controlled Autonomous Agent (Roadmap)

> **STATUS (2026-06-23): SHIPPED.** Phase 14 (14.1/14.2/14.3) merged to `main` via PR #11.
> Phase 15 shipped on `feat/phase-15-controlled-autonomy-agent`: 15.1 job-rank + **ADR-012**
> (`d43cde8`), 15.2 suggestion (`c7fb00e`), 15.3 interview sim (`755241b`), 15.4 briefing
> (`be8ae9c`), close-out (docs + ADR-012/013 ratified + autonomy/security audit). Autonomy
> boundary enforced by `test_autonomy_boundary.py` across all 5 agent surfaces. Deferred
> items below remain deferred (runtime-plugin engine, cloud, API exposure, Win/Linux pkg,
> authn, auto-apply/outreach — **never**, ADR-012). Entry-bundle 80.8 kB breach predates
> Phase 15 (Phase-14 condition); see `docs/PERFORMANCE_LOG.md`.

**Branch:** `feat/phase-14-15-hardening-and-agent` (cut off `main` after Phase 13 merged — it is,
`b77e143`, PR #10).
**Predecessor:** Phases 0–13 shipped. The strategy/career engines (**Phase 9**), the flywheel +
multi-tenant substrate (**Phase 12**), the surfaced UI + onboarding + macOS DMG + signed
auto-update (**Phase 13**, ADR-008/009/010/011) all exist.
**Phase ends at 14-15.8 (close-out).** No 14-15.9+.

---

## Why batch 14 + 15 together

Phases 12–13 burned time on too-small segments and repeated restarts. Phase 14–15 is batched into
**8 coarse segments** (3 for 14, 4 for 15, 1 close-out) — each a single cohesive commit, each
self-contained, copy-one-block-per-session. The reason it *fits* in 8: like Phase 13 reconciled the
"full multi-tenant SaaS" brief against shipped reality, Phase 14–15 reconciles the
"platform hardening + autonomous agent" brief against what's already built. Most of it is
**surface + orchestrate + draw a boundary (ADR)**, not net-new engines.

## Reconciliation — brief vs shipped reality

### Phase 14 (hardening / deployment / ecosystem)

| Brief item | Shipped already | Phase 14 disposition |
|---|---|---|
| 1. Deployment (DMG / Win / Linux) | macOS DMG signing/notarize **configured** (13.8, `PACKAGING.md`); not release-verified | **Release-verify the DMG** on a real machine + record cold-start → 14.1. Win/Linux **deferred** (13.8.1/.2) unless requested. |
| 2. Local + cloud hybrid (optional) | ADR-001 local-first; auto-update is the **only** net channel (13.9/ADR-011) | **REJECT cloud sync** — ADR note in 14.3. No build (ponytail rung 1; cloud "never required" per brief). |
| 3. Versioning (semver / migration-safe / rollback / prompt-lock / model-track) | prompt-version lock (`PromptVersion`, ADR-010); model keep_alive/build (12.5); Alembic; prompt + updater rollback | **Consolidate into a versioning/reproducibility spine** → 14.1. Net-new: one semantic **app version** surfaced + model-version tracking surface. |
| 4. Observability / telemetry (local-first) | `backend/observability.py` (latency), `services/observability/`, route, `PERFORMANCE_LOG.md` | **Add drift metrics** (ATS accuracy drift, resume success rate, embedding quality drift) + local dashboard → 14.2. No external telemetry (kept). |
| 5. Plugin system finalization (registry/lifecycle/permissions/isolation) | "plugins" = the **Claude dev workflow** (`docs/07`), not a runtime plugin engine | **DEFER a runtime plugin engine** (speculative for a single-user local app); **formalize the existing service-module boundary + dev-plugin contract** via ADR → 14.3. |
| 6. Security hardening (sandboxed ingest / no-exec / path validation / encrypted storage) | `ingestion/security.py` (allowlist+size+malformed-catch), asset:// chokepoint (13.8), no eval | **Final consolidated audit** + **optional** encrypted local storage (off by default) → 14.3. |
| 7. Ecosystem readiness (3rd-party plugins / job-board / ATS / API exposure) | none (future); job ingestion is paste-JD (local-first) | **DEFER** 3rd-party/API-exposure/job-board net integrations (ADR, 14.3). Job ingestion handled by **15.1** (paste/saved JD). |
| 8. Stability guarantees (no corruption / safe recovery / **deterministic seeded gen** / **reproducible ATS**) | backup/recovery (11.4), `integrity.py`, seed infra (12.x) | **Determinism + reproducibility tests** (seeded resume gen byte-stable; ATS score reproducible) → 14.1. |

### Phase 15 (controlled autonomous career agent)

| Brief item | Shipped already | Phase 15 disposition |
|---|---|---|
| 1. Job discovery & prioritization (rank / priority / explain / success-prob) | `services/strategy/application_strategy.py` (`ApplicationStrategyEngine`, `PrioritizeRequest`), `role_fit_scorer.py`, `skill_gap_forecaster.py` | **Surface** the existing engine as a ranked, explained, success-prob job view (paste/saved JD) → 15.1. |
| 2. Daily career briefing (jobs / gaps / resume tweaks / ATS / follow-ups) | composable from strategy + flywheel + ATS + CRM; no orchestrator | **Build the off-hot-path orchestrator + briefing surface** → 15.4. |
| 3. Application suggestion (Apply/Skip/Tailor; resume + CL + interview-prob; **NO auto-apply**) | `resume_strategy_selector.py`, cover-letter `tone`, `role_fit_scorer.py`, `ApplicationsPage` | **Surface per-application recommendation**; **hard no-auto-submit** (enforced + tested) → 15.2. |
| 4. Interview simulation (mock / recruiter behavior / follow-ups / KG answer eval) | `services/questions/generator.py`, `InterviewPrepPage.tsx` (panel + cadence), `services/knowledge_graph/` | **Deepen** existing: recruiter-behavior sim + follow-up generation + KG answer eval → 15.3. |
| 5. Career goal alignment (short/mid/long-term) | `services/strategy/career_path_simulator.py` | **Surface** trajectory alignment in the briefing → 15.4. |
| Autonomy boundaries (recommend ✔ / submit ✖ contact ✖ external-modify ✖ act-without-approval ✖) | ADR-010 precedent (propose-never-promote) | **ADR-012 controlled-autonomy framework** — written FIRST in 15.1; enforced + tested in 15.1/15.2/15.4. |

## Segment map (dependency-ordered) — 8 segments

```
Phase 14 — Hardening / deployment readiness
  14.1  Versioning & reproducibility spine        ← 13 ✓   (semver app-version + model-track + prompt-lock consolidate
                                                            + deterministic seeded gen + reproducible ATS + DMG release-verify)
  14.2  Observability & drift dashboard           ← 14.1   (ATS/success/embedding drift over observability.py + local FE dashboard)
  14.3  Security audit + ecosystem/plugin recon   ← 14.1   (final audit + optional encrypted storage + ADR-013 plugin/ecosystem/cloud DEFER)

Phase 15 — Controlled autonomous career agent (recommend-never-act)
  15.1  Autonomy framework (ADR-012) + job prioritization surface   ← 14 stable   (ADR FIRST; then surface ApplicationStrategyEngine)
  15.2  Application suggestion (Apply/Skip/Tailor)                   ← 15.1        (resume/CL/interview-prob; HARD no-auto-submit)
  15.3  Interview simulation deepening                              ← 15.1        (recruiter behavior + follow-ups + KG answer eval)
  15.4  Daily briefing + goal alignment                            ← 15.1,15.2   (off-hot-path orchestrator; hookify schedule; Dashboard surface)

Close-out
  14-15.8  Docs + ADR ratification (012, 013) + security/privacy review + roadmap annotation → merge to main
```

**Critical path:** `14.1 → 14.2/14.3 (parallel) → 15.1 → {15.2, 15.3 parallel} → 15.4 → 14-15.8`.
ADR-012 in 15.1 is the gate everything autonomous depends on — write it before any agent surface.

## ADRs this phase produces

- **ADR-012 — Controlled-autonomy framework.** The agent MAY rank/recommend/generate/simulate; it
  MAY NOT submit applications, contact recruiters, modify external systems, or act without explicit
  user approval. Extends ADR-010's propose-never-promote pattern to the whole agent layer. Defines
  the enforced boundary (no outbound action path exists in code) + the audit/explainability
  requirement. Written in 15.1; ratified in close-out.
- **ADR-013 — Plugin / ecosystem / cloud scope.** Records the deliberate **deferral**: no runtime
  plugin engine, no cloud-sync, no public API-exposure, no third-party/job-board net integrations
  for the single-user local-first app. Formalizes the *existing* service-module boundary + the
  Claude dev-workflow "plugin orchestration" (`docs/07`) as the plugin contract that actually
  governs the repo. Written in 14.3; ratified in close-out. (Ponytail rung 1: burden is on building,
  not deferring.)

## Carried-forward gates (every applicable segment)

- **No hallucination + 3-level confidence (ADR-006)** on every user-facing figure/recommendation —
  `verified` / `strong_inference` / `weak_inference`; **success-probability / interview-probability
  are estimates** and must carry a confidence + evidence, never a bare number; low-n de-emphasized.
- **Autonomy boundary (ADR-012):** any agent surface must have **no code path** that submits/contacts/
  mutates an external system; a test asserts the boundary (mirror 13.6's "never promotes" test).
- **TDD** (failing test first, ≥90% on new code, suite green); **pyright** / **tsc**; per-segment
  **code-review**; **security-review** on 14.3 (encrypted storage / audit) + 15.x (autonomy).
- **Frontend perf gates** (Phase 11 standard): 60fps, 0 long-tasks during interaction, CLS ≈ 0,
  entry bundle ≤ 80.8 kB gz, capability tiers honored (Off usable), CSP unchanged.
- **verification-before-completion:** every "done"/"gate held" claim backed by a real command +
  pasted number (coverage %, pytest/bench output, live perf trace).

## Deferred (recorded, not dropped)

| Item | Why deferred | Reopen when |
|------|--------------|-------------|
| Runtime plugin engine (registry/lifecycle/permissions/isolation) | Speculative for single-user local; service-module boundary already isolates domains | a real third-party extension is wanted (ADR-013) |
| Cloud sync / hybrid mode | ADR-001 local-first; brief says cloud "never required" | a user explicitly opts into multi-device sync → own ADR |
| Public API-exposure layer · third-party / job-board / external-ATS net integrations | No network listener for other principals (ADR-008); local-first | network exposure / multi-user is chosen → own brainstorm+ADR |
| Windows / Linux packaging (13.8.1/.2) | macOS is dev/target platform | a non-mac target is requested |
| Real authentication / gate `X-Tenant-Id` | Local-only; carried from Phase 13 (ADR-008 §Forward-looking) | any network exposure / shared deploy |
| Auto-apply / recruiter outreach | **Hard product boundary (ADR-012)** — never | never (out of scope by decision) |
| msgpack IPC · FAISS · Nuitka · pinned-memory (12.9 backlog) | All VOID; no measured reopen condition fired | `docs/optimization/deferred-optimization-backlog.md` condition fires with a number |

## Token-efficiency ("Both")

- **Dev-time (every segment):** RTK on shell ops · caveman+ponytail prose · ONE `context7` batch up
  front · ONE read pass bounded to the segment spec + only touched files · land small. Baked into the
  session-wide invariants in `phase-14-15-segment-prompts.md`.
- **Runtime:** 14.2 drift metrics must be **off-hot-path** (computed on a schedule/rollup, not per
  request); 15.4 briefing orchestrator is **off-hot-path** (like 13.6). No per-request cost added.
