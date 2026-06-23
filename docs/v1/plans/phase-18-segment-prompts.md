# Phase 18 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. **6 segments** (5 build + close-out).
Map + reconciliation: `phase-18-roadmap.md`. **Final phase of v1** — ends at **18.6**; after it,
all work is adhoc/v2 (`docs/v2/`).

## Recommended order (dependency-correct)

```
18.1 de-personalization + generalized onboarding   FIRST — can't ship an alpha that leaks the dev's data
18.2 feature-flag system + local A/B (ADR-020)      ← 18.1
18.3 local-only telemetry aggregates               ← 18.1
18.4 versioned build + rollback + xplat framework   ← 18.2
18.5 update mechanism (ADR-020)                     ← 18.4
18.6 multi-user audit + ecosystem recon + close     ← all   v1 DONE
```

## Session-wide invariants (true for ALL — stated once)

- **Branch:** `feat/phase-18-alpha-release` (off `main`, Phase 17 merged). One commit/segment.
  **PR deferred to 18.6.** Git Attribution: NO Claude/Anthropic in commits/PRs/branches.
- **Rules (CLAUDE.md):** no hallucination + ADR-006 (generalized onboarding builds honest profiles
  from real uploads — thin data → labeled-empty/`weak_inference`, never fabricated); read `docs/`
  first; **`context7` for APIs** (Tauri bundler/updater, GitHub Releases manifest, Argon2 — never
  from memory). TDD: failing test FIRST, ≥90% new code, suite green. Ponytail: rung 1. Caveman:
  terse; code/security normal.
- **Phase-18 strict rules (assert, don't claim):** NO silent updates · NO forced updates · NO data
  sharing without explicit user control · NO breaking changes without version migration. Each has a
  test (updater only *checks*; telemetry payload has no PII; a schema change without a down-migration
  is blocked).
- **Plugins:** `commit-commands` (release tagging) · `pr-review-toolkit` (validation, 18.6) ·
  `security-guidance` (final audit, 18.6) · `claude-md-management` (release docs, 18.6).
- **Carried boundaries:** recommend-never-act (ADR-012); multi-user isolation (16.x) holds under
  alpha; update channel = ADR-011 (one signed, TLS-only, data-free check); ADR-020 governs
  distribution/flags/update.
- **Token-efficiency:** RTK · ONE `context7` batch · bounded read pass. Telemetry + any rollups run
  **off-hot-path** (reuse the 13.6/14.2 scheduler seam — NO new scheduler); flag lookup is a local
  map read; update check is data-free.
- **Shipped surface you build on (verify shapes — don't assume):**
  - **Onboarding/profile:** `routes/onboarding.py`, `frontend/src/pages/FirstRunWizard.tsx`,
    `backend/services/profile/`, **the seeded Andrew data** `.static_files/profile/` (+ `resumes/`,
    `cover-letters/`, `job-descriptions/`, `resources/`) — the thing 18.1 removes from the public repo.
  - **Profile-building engines (Phase 9 / KG):** `services/knowledge_graph/` (skill graph),
    `services/ats/` (ATS baseline), `services/cover_letter/` (writing/voice profile),
    `services/strategy/career_path_simulator.py` (career profile).
  - **Versioning (14.1):** `routes/health.py` (`GET /health/version`), `backend/config.py` +
    `frontend/src-tauri/tauri.conf.json` (single-source semver), `docs/VERSIONING.md`. **Migrations:**
    Alembic up/down. **Packaging (13.8):** `tauri.conf.json` (bundle/updater), `lib.rs`,
    `docs/PACKAGING.md`.
  - **Telemetry feed:** `backend/observability.py` + `services/observability/` (latency + 14.2
    drift), `models/signal.py`/`metric.py`, audit events (16.3). **Scheduler seam:** the 13.6
    `evolution_loop` / `routes/maintenance.py`.
  - **Settings/config:** `routes/settings.py`, `models/system_config.py`, `SettingsPage.tsx`.

---

## 18.1 — De-Personalization + Generalized Onboarding

Implement Phase 18.1 — remove every reference to Andrew from the public repo (Q11) and generalize
onboarding so **any** user's uploads build all four profiles (skill graph, ATS baseline, writing
profile, career profile). Brief item 2 + the multi-user precondition. **FIRST** — an alpha cannot
leak the developer's data.

PRECONDITION: Phase 17 merged. Onboarding wiring exists but is seeded to Andrew (`.static_files/
profile/`); the profile-building engines exist (KG / ATS / cover-letter voice / career simulator).

Read first (STOP at the seeded data + the onboarding ingest path): (1) `phase-18-roadmap.md`. (2)
`.static_files/` (the seeded Andrew profile/resumes/CL/JDs — what references him) + a repo-wide grep
for personal identifiers (name/email/employers/projects). (3) `routes/onboarding.py` +
`FirstRunWizard.tsx` + `services/profile/` (the upload→profile pipeline). (4) the four engines that
build profiles from uploads (KG skill graph, ATS baseline, CL writing/voice, career simulator).

Order: brainstorm (confirm: (A) **de-personalize** — the seeded Andrew corpus moves out of the
public repo (into a gitignored/local-only sample or a synthetic demo tenant behind a flag, NOT the
default); the public repo has no Andrew identifiers; (B) **generalize** — onboarding accepts any
user's resume/CL uploads + optional GitHub + optional job history → builds skill graph + ATS baseline
+ writing profile + career profile per tenant) → ADR? skip (consumes ADR-014 multi-tenant) → TDD
(onboarding a fresh fixture user builds all four profiles from *their* uploads; **a new user with no
data gets labeled-empty profiles, never Andrew's / never fabricated** (ADR-006); a repo scan asserts
no personal identifiers remain in public paths) → implement → verify.

Traps: (1) **No leakage of the dev's data** — the seeded corpus is NOT the default for a new tenant;
grep proves the public repo is clean (Q11). (2) **Honest empties** — thin/no upload → `DormantEmpty
State`/`weak_inference`, never invented history (ADR-006). (3) **Per-tenant** — profiles build into
the authenticated tenant's store (16.1); no shared/global profile. (4) **Optional inputs** — GitHub +
job history are optional; onboarding completes without them. (5) ponytail: reuse the existing engines;
18.1 wires uploads→engines + strips the seed, it doesn't rebuild profile-building.

Files: move/gitignore `.static_files/` seed (or gate as a synthetic demo tenant), EDIT
`routes/onboarding.py` + `FirstRunWizard.tsx` + `services/profile/`, a repo-clean scan test +
onboarding tests + fixtures. Def-of-done: public repo free of personal identifiers (scan-asserted) +
generalized onboarding builds all four profiles from any user's uploads + honest empties + per-tenant,
suites green, commit.

---

## 18.2 — Feature-Flag System + Local A/B (ADR-020)

Implement Phase 18.2 — a local feature-flag store with deterministic-hash A/B bucketing and
flag-flip rollback. Brief items 1 (flags) + 5; **ADR-020** (flag/rollout part). Q14: local,
deterministic, no server.

PRECONDITION: 18.1. Settings/config exist (`system_config.py`, `routes/settings.py`).

Read first (STOP at the config store + a call site that would gate a feature): (1) ADR-020
(drafted). (2) `models/system_config.py` + `routes/settings.py` (the local config store flags
extend). (3) a feature surface to gate (e.g. a 15.x/17.x view) as the first consumer.

Order: ratify ADR-020 (flag part) → TDD (a flag read returns its value from local config;
**deterministic A/B** — `hash(tenant_id ‖ flag_key)` → stable bucket, same input → same bucket
across runs (no server); flipping a flag off disables the feature without a rebuild — rollback;
default values are safe-off for in-progress features) → implement (a small flag module: read/eval +
deterministic bucket; gate one real feature as the proof) → verify.

Traps: (1) **Deterministic + offline** — bucketing is a pure hash, reproducible, no assignment
server (Q14). (2) **Safe rollback** — a broken feature dies by flag flip, not a rebuild/redeploy.
(3) **Default-off for in-progress** — a half-built feature ships behind an off flag. (4) ponytail:
local map + a hash; no flag-service, no remote config (rung 1 — local-first).

Files: ratify ADR-020 (flag section), NEW flag module + flag config in `system_config.py`/Settings,
gate one feature, tests. Def-of-done: local flag store + deterministic offline A/B bucket +
flag-flip rollback + one feature gated as proof, suites green, commit.

---

## 18.3 — Local-Only Telemetry Aggregates

Implement Phase 18.3 — local-only aggregate telemetry: system performance, feature-usage counts,
anonymized success rates. **No personal data leaves the system.** Brief item 4. Off-hot-path over
existing signals.

PRECONDITION: 18.1. Observability/drift (14.2) + audit events (16.3) + signal models exist.

Read first (STOP at the signal sources + the scheduler seam): (1) `backend/observability.py` +
`services/observability/` (latency + drift). (2) `models/signal.py`/`metric.py` + the 16.3 audit
events (usage counts source) + flywheel `feedback.py` (success-rate rollups). (3) the 13.6/14.2
scheduler seam (reuse — NO new scheduler). (4) a place to surface it (Settings or a local stats
view).

Order: brainstorm (confirm: an **off-hot-path** rollup computing perf summaries + feature-usage
counts + anon success rates over existing signals; surfaced locally; **payloads contain no PII** and
**nothing leaves the machine**) → ADR? skip (consumes ADR-011 boundary; local-only reaffirmed) →
TDD (aggregates compute correctly on a fixed signal fixture; **a test asserts the telemetry payload
has no personal fields** and there is **no outbound call**; low-n → suppressed not fabricated;
counts are counts, not record contents) → implement (rollup on the existing seam; local surface) →
verify.

Traps: (1) **Local-only, no exfil** — zero network; a test asserts no outbound call (the only net
channel is the ADR-011 update check, data-free). (2) **Aggregates, not records** — counts + rates +
perf, never bodies/PII (ADR-016 digests precedent). (3) **Off-hot-path** — reuse the 13.6/14.2 seam;
no per-request cost (assert). (4) **Anon success rates** — k-anonymity/low-n suppression precedent
(ADR-009); thin data → no confident number. (5) ponytail: descriptive aggregates; no model.

Files: NEW aggregate methods in `services/observability/`, schedule on the existing seam, a local
surface (EDIT `SettingsPage`/a stats view), tests. Def-of-done: local-only perf + usage-count +
anon-success aggregates, off-hot-path, **no PII / no outbound (asserted)**, low-n suppressed,
suites green, commit.

---

## 18.4 — Versioned Alpha Build + Rollback + Cross-Platform Framework

Implement Phase 18.4 — produce a versioned alpha DMG on the 14.1 spine, with rollback (retained
prior builds + Alembic down-migration gate) and a Win/Linux **framework** (scaffolded, not built).
Brief items 1 + 6; **ADR-020** (build part). Q10/Q13.

PRECONDITION: 18.2. Versioning spine (14.1) + DMG config (13.8) exist; **no Apple cert (Q13)**.

Read first (STOP at the version source + the bundle config): (1) ADR-020. (2) `tauri.conf.json`
(bundle/targets) + `backend/config.py` (single-source semver, 14.1) + `routes/health.py`. (3)
Alembic up/down + the migration gate concept. (4) `docs/PACKAGING.md` (current DMG steps). `context7`
the Tauri bundler + multi-target config.

Order: ratify ADR-020 (build part) → TDD/gates (a build carries the 14.1 semver + migration head;
**a schema change lacking a down-migration is blocked** (the no-breaking-change-without-migration
rule); rollback = reinstall prior DMG + `alembic downgrade` to that head, demonstrated on a temp db)
→ build (unsigned/ad-hoc DMG — document Gatekeeper quarantine workaround honestly, Q13; retain the
prior build artifact for rollback) → scaffold Win/Linux Tauri targets (config only, NOT built, Q10)
→ verify (build the DMG, launch on a clean machine, **record cold-start** — the 14.1/12.9.3 gate;
paste it).

Traps: (1) **Unsigned, honest** — no notarization (Q13); document the workaround, don't fake signed.
(2) **Down-migration gate** — a breaking schema change must ship a tested downgrade or it's blocked
(strict rule, tested). (3) **Retain builds** — rollback needs the prior artifact kept. (4)
**Framework only for Win/Linux** — configure targets, build nothing (ponytail rung 1; Q10). (5)
cold-start recorded honestly (>400ms = a backlog note, not a build).

Files: ratify ADR-020 (build), EDIT `tauri.conf.json` (targets + version) + `docs/PACKAGING.md`
(unsigned DMG + Gatekeeper + rollback steps) + a migration-gate check + `docs/PERFORMANCE_LOG.md`
(cold-start), tests. Def-of-done: versioned unsigned DMG (14.1 spine) + rollback (retained build +
down-migration gate, demonstrated) + Win/Linux framework scaffolded + cold-start recorded, commit.

---

## 18.5 — Update Mechanism (ADR-020)

Implement Phase 18.5 — an in-app "update available" **check** (manual download; no silent/forced
install), GitHub-Releases-ready but alpha-on-a-static-manifest. Brief item 6 (update); **ADR-020**
(update part) honoring **ADR-011**.

PRECONDITION: 18.4 (versioned builds + the version endpoint). ADR-011 channel boundary exists.

Read first (STOP at the version endpoint + the updater config): (1) ADR-020 + ADR-011 (the data-
free, no-silent-update boundary). (2) `routes/health.py` (`GET /health/version` — the current
version to compare) + `tauri.conf.json` updater config (13.8). (3) `context7`: a version-manifest
check (GitHub Releases shape) — but the source must be pluggable.

Order: ratify ADR-020 (update part) → TDD (the check fetches a version manifest and reports
"update available" when remote > local; it **never downloads or installs** silently/forcibly — only
notifies (assert); the manifest source is pluggable (static file for alpha, GitHub Releases later);
the check is data-free — only a version string crosses, ADR-011) → implement (in-app check + a
"new version — download" notice pointing to the manual download; GitHub-Releases adapter behind the
pluggable source, off for alpha) → verify (against a fixture manifest).

Traps: (1) **Check, never push** — no auto-download, no forced install (strict rule + ADR-011,
tested). (2) **Data-free** — only a version string leaves; no telemetry rides the check (ADR-011).
(3) **Pluggable source** — static manifest now, GitHub Releases door open (Q12) — don't hard-wire.
(4) **User-controlled** — the user clicks to download; the app keeps working on the old version.

Files: ratify ADR-020 (update), NEW update-check (FE notice + a thin version-compare, pluggable
source), EDIT `tauri.conf.json`/docs, tests against a fixture manifest. Def-of-done: in-app
update-available check (notify-only, manual download, data-free) + pluggable GitHub-Releases-ready
source + no silent/forced update (asserted), suites green, commit.

---

## 18.6 — Multi-User Safe-Mode Audit + Ecosystem Recon + v1 Close-out

Run Phase 18.6 — audit multi-user safety at alpha scale, record ecosystem-readiness as deferred-
future (v2), final security audit, ratify ADR-020, docs → merge. **This closes v1.** Brief items
3 + 7. `security-guidance` final audit + `pr-review-toolkit`.

PRECONDITION: 18.1–18.5 shipped. First action: enumerate shipped + deferred (plugin marketplace,
ATS/job-board APIs, enterprise, signed/notarized DMG, Win/Linux builds, cloud sync).

Read first (STOP at the isolation tests + the deferred tables): (1) `phase-18-roadmap.md` +
`phase-16-roadmap.md` (the isolation tests to re-run at alpha scale). (2) `docs/v2/ROADMAP.md` (the
ecosystem items land here as future). (3) `MEMORY.md` ledger + `docs/SECURITY_DEPENDENCIES.md`.

Order: a checklist. (1) **Multi-user safe-mode audit:** re-run/extend the Phase-16 isolation tests
at alpha scale — strict tenant isolation, no cross-user leakage, **no shared embeddings, no shared
personal memory** (the brief's item 3, each test-backed). (2) **Ecosystem-readiness recon:** record
plugin marketplace + external ATS/job-board integrations + enterprise deployment as **deferred-future
(v2)** in `docs/v2/ROADMAP.md` — the permission model (ADR-018) is the only readiness primitive built;
no new code. (3) **Final security audit:** `security-guidance` end-to-end across the alpha surface —
no silent updates, no forced updates, no data sharing without consent, no breaking change without
migration (the four strict rules, each test-backed). (4) **Docs:** `README` (alpha install/Gatekeeper),
`USER_GUIDE`, `08_ROADMAP` (v1 complete block), `ARCHITECTURE_OVERVIEW`, `02_TECHNICAL_ARCHITECTURE`,
`PACKAGING`, `VERSIONING`, `INDEX`. (5) **ADR:** ratify ADR-020. (6) **Roadmap annotation + v1 close:**
mark Phases 16–18 shipped; state plainly v1 is done and future work is adhoc/v2.

Traps: (1) **verification-before-completion** — isolation + the four strict rules backed by re-run
output, not asserted; the DMG actually launches on a clean machine. (2) **Close out only what
shipped** — the ecosystem items are deferred *to v2*, documented in `docs/v2/`, not dropped or faked.
(3) **The headline:** v1 final state — local-first career OS · recommend-never-act agent (ADR-012) ·
multi-tenant (ADR-014) · browser-capture (ADR-019) · alpha-distributable (ADR-020). (4) ponytail/
caveman pass: no marketplace/enterprise/cloud crept in (all v2).

Plugins: `security-guidance`, `pr-review-toolkit`, `commit-commands` (tag the alpha release),
`claude-md-management`, `code-review`, `verification-before-completion`. Files: isolation audit
tests, `docs/v2/ROADMAP.md` (ecosystem deferrals), docs edits, ADR-020 ratification, roadmap
annotation — no new services. Def-of-done: multi-user safe-mode audited (isolation/no-shared-
embeddings-or-memory, test-backed) + ecosystem recorded deferred-to-v2 + four strict rules audited
+ docs + ADR-020 ratified + alpha tagged → **Phase 18 ready to merge to `main` — v1 COMPLETE.**
