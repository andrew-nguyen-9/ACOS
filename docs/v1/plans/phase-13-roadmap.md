# Phase 13 — Surfacing · Onboarding · Packaging · Automation (Roadmap)

**Branch:** `feat/phase-13-surfacing-onboarding-packaging` (cut off `main` *after* Phase 12 merges;
if Phase 12 is not yet merged, base off `feat/phase-12-velocity-flywheel-multitenant` HEAD `aafea4c`).
**Predecessor:** Phase 12 shipped the backend flywheel + multi-tenant foundation (12.10–12.16,
ADR-008 isolation, ADR-009 aggregation). Routes exist; **no frontend consumes them.**
**Phase ends at 13.11 (close-out).** No 13.12+.

---

## Why this phase

Phase 12 built the engine and left it headless. Phase 13 surfaces it, gives new users a way in
(onboarding/cold-start), reclaims the displaced packaging milestone (M5), and closes the loop with
an approval-gated automation job — without breaking the local-first invariants except the one
network exception the user explicitly chose (background auto-update, ADR-011).

The generic "full multi-tenant SaaS" brief was reconciled against shipped reality: tenant model,
isolation, and the prompt-version substrate already exist (Phase 12). `supabase` / network /
"scalable SaaS" are **out** (ADR-001/008 local-first). What remained non-redundant became the
8 themes below.

## Theme → disposition

| # | Theme | Disposition | Lands in |
|---|-------|-------------|----------|
| 1 | Surface the flywheel (no UI) | ✅ **Primary** | 13.0–13.4 |
| 2 | Multi-profile UX | ❌ Deferred — substrate only (single `default` profile) | — (note in 13.11) |
| 3 | Chroma tenant read-filter completion | ❌ Deferred — no 2nd profile exists; trivial+pointless at k=1 (ADR-008 §"Chroma read-filter status") | — |
| 4 | Authentication | ❌ Stays deferred; local-only boundary **re-recorded** (ADR-008 §Forward-looking) | 13.11 |
| 5 | Prompt-evolution automation loop | ✅ In | 13.6 (ADR-010) |
| 6 | Packaging & release (DMG, wizard, auto-update, notes) | ✅ **Reclaimed** | 13.7–13.9 |
| 7 | Deferred-optimization backlog | ✅ Re-baseline check only (stays VOID without a measured number) | 13.10 |
| 8 | Verification debt (live-Ollama bench, golden-set harness, ≥5-profile demo) | ✅ In | 13.10 |

## Segment map (dependency-ordered)

```
Track A — Surface the flywheel (PRIMARY, frontend)
  13.0  FE flywheel data layer + confidence/empty-state primitives   ← 11.5 design system ✓
  13.1  Skill-ROI dashboard            ← 13.0   (extend LearningPage; GET /flywheel/skills/roi)
  13.2  Resume-editor strategy hints   ← 13.0   (extend ResumePage; GET /flywheel/strategy)
  13.3  Global-pattern suggestions     ← 13.1   (extend LearningPage; GET /flywheel/global/roi; k<5 dormant)
  13.4  Prompt-evolution review/approval UI ← 13.0  (extend OptimizationPage; propose/trial/promote/rollback + audit)

Track B — Cold-start + onboarding UX
  13.5  Onboarding doc-upload + cold-start surfacing ← 13.0   (extend FirstRunWizard profile step)
        └ 13.5.x  split if it balloons (upload pipeline / graph-build / Career-Voice surfacing)

Track C — Automation (theme 5)
  13.6  Prompt-evolution automation loop ← 13.4   ADR-010   (ralph-loop off-hot-path; NEVER auto-promotes)

Track D — Packaging & release (theme 6, reclaimed)
  13.7  First-run model-pull progress + DMG first-run hook ← 13.5   (extend existing FirstRunWizard)
  13.8  macOS DMG (tauri build) + signed artifact
        └ 13.8.1 Windows · 13.8.2 Linux   (roadmap backlog — only if requested)
  13.9  Background auto-update + release notes   ADR-011  ⚠️ NETWORK BOUNDARY (security-review required)

Track E — Verification debt + opt re-baseline (themes 7, 8)
  13.10 Live-Ollama bench runner (8a) + scored golden-set retrieval harness (8b)
        + 12.0 re-baseline → check deferred-backlog reopen conditions (theme 7)
        + global-aggregation exercise via synthetic ≥5-profile fixture (8c)

Track F — Close-out
  13.11 Docs + ADR ratification (010, 011) + roadmap annotation + security/privacy review → merge to main
```

**Build order:** `13.0 → 13.1 → 13.4 → 13.6` is the critical path (gate before the thing that feeds
it). `13.2 · 13.3 · 13.5` parallel after `13.0`/`13.1`. Packaging `13.7 → 13.8 → 13.9` after the
surfaced UI is stable. `13.10` near the end. `13.11` last.

## ADRs this phase produces

- **ADR-010 — Autonomous prompt-evolution loop.** A background job may *propose* prompt candidates
  from success signals but **never auto-promotes**; promotion stays human-approved (13.4 gate).
  Documents the guardrails, the off-hot-path execution, and the propose-only autonomy boundary.
- **ADR-011 — Background auto-update & the network exception.** Auto-update breaks the CLAUDE.md
  local-only/no-network default **by explicit user decision.** ADR-011 scopes the break: update
  channel only, **signed updates verified before apply**, TLS, no telemetry beyond the version
  check, user-visible. Cross-references ADR-008 §Forward-looking — if the update channel ever
  carries identity, the `X-Tenant-Id` IDOR note becomes live. `security-review` is mandatory.

## Carried-forward gates (every applicable segment)

- **No hallucination + 3-level confidence (ADR-006)** on every user-facing figure/recommendation —
  `verified` / `strong_inference` / `weak_inference`; synthetic/cold-start inference **clearly
  labeled**; low-n excluded from "recommended."
- **TDD** (failing test first, ≥90% on new code, suite stays green); **pyright** (backend) / **tsc**
  (frontend); **per-segment code-review**; **security-review** on 13.9 (network) + 13.6 (autonomy).
- **Frontend perf gates** (Phase 11 standard): 60fps, 0 long-tasks during interaction, CLS ≈ 0,
  entry bundle ≤ 80.8 kB gz, capability tiers honored (Off tier usable), CSP unchanged except the
  deliberate 13.9 update-origin allowance.
- **verification-before-completion:** every "done"/"budget held" claim backed by a real command +
  number (paste coverage % + pytest/bench output).

## Deferred (recorded, not dropped)

| Item | Why deferred | Reopen when |
|------|--------------|-------------|
| Multi-profile create/switch UI | Substrate-only decision; one `default` profile today | a real 2nd local profile is wanted |
| Chroma tenant read-filter + reindex backfill | Pointless at k=1 tenant (ADR-008) | 2nd profile's RAG must be trusted |
| Authentication / gate `X-Tenant-Id` | Local-only, no network listener for other principals | any network exposure / multi-user / shared deploy |
| Windows / Linux packaging (13.8.1/.2) | macOS is the dev/target platform | a non-mac target is requested |
| msgpack IPC · FAISS · Nuitka · pinned-memory (12.9 backlog) | All VOID; no measured reopen condition fired | `docs/optimization/deferred-optimization-backlog.md` condition fires with a number |
| PyO3 singularity (12.9.4 → Phase 13 epic) | Request-path latency is **not** the measured bottleneck (12.2–12.6 captured the win) | request-path latency becomes a measured bottleneck → own brainstorm+ADR |

## Token-efficiency ("Both")

- **Dev-time (every segment):** RTK proxy on shell ops · caveman+ponytail prose · ONE `context7`
  batch up front · ONE read pass bounded to the segment spec + only touched files · land small.
  Baked into the session-wide invariants in `phase-13-segment-prompts.md`.
- **Runtime:** 13.10 re-baselines the 12.0 harness against real payloads and checks each
  deferred-backlog reopen condition. No reopen without a measured number — they stay VOID
  (Ponytail rung 1; burden is on adopt, not defer).
