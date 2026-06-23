# Phase 18 — Alpha Release, Onboarding & Distribution (Roadmap)

> **STATUS (2026-06-23): SHIPPED on `feat/phase-18-alpha-release` (stacked on phase-17, NOT
> pushed). FINAL PHASE — v1 COMPLETE.** 6 segments: 18.1 de-personalization (FirstRunWizard
> placeholder genericized, `.static_files/` already gitignored, repo-clean scan test) · 18.2
> feature flags + deterministic offline A/B (ADR-020) · 18.3 local-only telemetry aggregates
> (no PII / no network, low-n suppressed) · 18.4 migration down-gate (every revision has a real
> downgrade) + unsigned-DMG/rollback docs · 18.5 notify-only data-free update check (pluggable
> source) · 18.6 multi-user safe-mode audit (no shared embeddings/memory) + ecosystem recon →
> v2 + ADR-020 ratified. Suite 1180+ green. Deferred → `docs/v2/ROADMAP.md`: plugin marketplace,
> ATS/job-board APIs, enterprise, signed/notarized DMG, Win/Linux builds, cloud sync. After 18,
> all work is adhoc/v2.

**Branch:** `feat/phase-18-alpha-release` (cut off `main` after Phase 17 merges).
**Predecessor:** Phases 0–17 shipped. Exists: versioning spine (14.1, `VERSIONING.md`,
`GET /health/version`), DMG packaging (13.8, `PACKAGING.md`), update channel boundary (ADR-011),
onboarding (`routes/onboarding.py`, `FirstRunWizard.tsx`, `services/profile/`), observability/drift
(14.2), auth + tenant isolation (16.1), encryption (16.2).
**Phase ends at 18.6 (close-out = v1 done).** No 18.7+.

---

## Why this is *generalize + package + record-deferred*, not net-new engines

The engines exist; Phase 18 makes them **shippable to someone who isn't Andrew**. The heavy
line item is **de-personalization** (Q11: the public repo has no references to Andrew; onboarding
builds every profile from the user's own uploads). The rest is packaging/rollout plumbing
(flags, telemetry aggregates, versioned builds, update check) on the 14.1 versioning spine and
the ADR-011 channel — and recording the ecosystem-readiness items as honest future/v2 deferrals.

## Reconciliation — brief vs shipped reality

| Brief item | Shipped already | Phase 18 disposition |
|---|---|---|
| 1. Alpha deployment (versioned / rollback / staged rollout / feature flags) | 14.1 version spine, Alembic up/down, ADR-011 channel | **Versioned builds + rollback + flag-gated rollout** → 18.2/18.4, **ADR-020**. |
| 2. Onboarding generalized (upload resume/CL, opt GitHub, opt job history → skill graph / ATS baseline / writing profile / career profile) | `FirstRunWizard.tsx`, `routes/onboarding.py`, `services/profile/`, Phase-9 engines — but **seeded to Andrew** (`.static_files/profile/`) | **De-personalize + generalize**: any user's uploads build all four profiles → 18.1. |
| 3. Multi-user safe mode (tenant iso / no leakage / no shared embeddings / no shared memory) | auth + isolation (16.1/16.5) | **Audit + assert** at alpha scale; reuse Phase-16 isolation tests → 18.6. |
| 4. Telemetry (local-only aggregates: perf / feature-usage counts / anon success rates) | observability/drift (14.2), audit events (16.3) | **Local-only aggregate rollups** over existing signals; **no PII out** → 18.3. |
| 5. Feature-flag system (phased rollout / A/B / safe rollback) | none | **Local flag store + deterministic-hash A/B** → 18.2, **ADR-020**. |
| 6. Distribution (signed DMG / installers / update mechanism) | DMG configured (13.8); ADR-011 channel; **no Apple cert (Q13)** | **Unsigned DMG + manual download + in-app update *check*** (no silent/forced); Win/Linux framework → 18.4/18.5, **ADR-020**. |
| 7. Ecosystem readiness (plugin marketplace / external integrations / enterprise — future) | permission model (ADR-018); none of the rest | **Record deferred-future (v2)** + readiness notes; no build → 18.6. |

## Segment map (dependency-ordered) — 6 segments

```
18.1  De-personalization + generalized onboarding       ← 17 ✓   remove Andrew from public repo (Q11); uploads → skill graph + ATS baseline + writing + career profile; multi-user safe
18.2  Feature-flag system + local A/B (ADR-020)          ← 18.1   local flag store; deterministic-hash bucket; flag-flip rollback
18.3  Local-only telemetry aggregates                   ← 18.1   perf + feature-usage counts + anon success rates over 14.2/16.3 signals; NO PII out
18.4  Versioned alpha build + rollback + xplat framework ← 18.2   DMG build on 14.1 spine; retain prior builds; Alembic down-migration gate; Win/Linux scaffold (no build)
18.5  Update mechanism (ADR-020)                         ← 18.4   in-app "update available" check; manual download; GitHub-Releases-ready door; Gatekeeper workaround doc
18.6  Multi-user safe-mode audit + ecosystem recon + close ← all  isolation audit at alpha scale; ecosystem/marketplace/enterprise → deferred-future; ADR ratify; v1 DONE → merge
```

**Critical path:** `18.1 → 18.2 → {18.3, 18.4} → 18.5 → 18.6`. De-personalization (18.1) gates
everything — you cannot ship an alpha that leaks the developer's data, and generalized onboarding
is the precondition for any non-Andrew tester.

## ADRs this phase produces

- **ADR-020** — Alpha distribution + update channel + feature-flag rollout (unsigned-mac alpha,
  manual download + in-app check, GitHub-Releases-ready, local deterministic A/B, Win/Linux
  framework; **honors ADR-011 + ADR-001**). Spans 18.2/18.4/18.5.

## Carried-forward gates (every applicable segment)

- **No silent updates, no forced updates, no data sharing without explicit user control, no
  breaking changes without version migration** (Phase-18 strict rules) — each asserted: a test
  confirms the updater only *checks*; a test confirms telemetry payloads contain no PII; a
  migration gate blocks a schema change lacking a down-migration.
- **No hallucination (ADR-006)** — generalized onboarding must build honest profiles from real
  uploads; a new user with thin data gets labeled-empty/`weak_inference`, never fabricated
  history (reuse `DormantEmptyState`).
- **Recommend-never-act (ADR-012)** and **multi-user isolation (16.x)** hold under alpha load.
- **TDD** + **pyright/tsc** + per-segment **code-review**; **`security-guidance` final audit** (18.6);
  **Frontend perf gates** on onboarding/settings/telemetry views.
- **verification-before-completion** — DMG actually built + launched on a clean machine; cold-start
  recorded (14.1 gate); update-check tested against a fixture manifest.

## Plugins (per `docs/07`)

`commit-commands` (release tagging) · `pr-review-toolkit` (release validation, 18.6) ·
`security-guidance` (final audit, 18.6) · `claude-md-management` (release docs, 18.6).

## Deferred (recorded, not dropped) — these define the v1/v2 line

| Item | Why deferred | Reopen when |
|------|--------------|-------------|
| Plugin marketplace / runtime third-party engine | Permission model only (ADR-018); marketplace is a v2 product surface | `docs/v2/ROADMAP.md` — real third-party demand |
| External ATS / job-board integrations | Outbound + per-vendor; conflicts with local-first + ADR-012 unless opt-in-exported | v2 — explicit opt-in export ADR |
| Enterprise deployment (org tenants / RBAC / admin) | Single-machine alpha; needs hosted/shared infra | v2 — enterprise ADR |
| Signed/notarized DMG + automated GitHub-Releases updates | No Apple cert yet (Q13); alpha is manual | a Developer ID cert exists → flip ADR-020 §1/§2 |
| Windows / Linux builds | macOS is the target; framework scaffolded only (Q10) | a non-mac alpha cohort is wanted |
| Cloud sync / multi-device | Local-first (ADR-001) | opt-in multi-device → own ADR |

## Token-efficiency ("Both")

- **Dev-time:** RTK · caveman+ponytail · ONE `context7` batch (Tauri bundler/updater, GitHub
  Releases manifest, Argon2 if onboarding re-keys) · bounded read pass.
- **Runtime:** telemetry aggregates computed **off-hot-path** (rollup over existing signals, reuse
  the 13.6/14.2 scheduler seam — no new scheduler, no per-request cost); feature-flag lookup is a
  local map read (no network); update check is user-initiated/periodic, data-free (ADR-011).

---

## v1 close-out (end state after 18.6)

ACOS is: a local-first AI career OS · a controlled autonomous career agent (recommend-never-act,
ADR-012) · a multi-tenant platform (auth + isolation, ADR-014) · a browser-integrated job-capture
system (ADR-019) · an alpha-distributable product (ADR-020). Everything beyond is **adhoc/v2** —
see `docs/v2/ROADMAP.md` and `docs/BACKLOG.md`.
