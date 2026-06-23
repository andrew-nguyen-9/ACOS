# Documentation Index

The complete map of ACOS documentation. Read this first to find the right document fast.

> **Reading order for newcomers:** [`01_PRODUCT_VISION`](01_PRODUCT_VISION.md) →
> [`ARCHITECTURE_OVERVIEW`](ARCHITECTURE_OVERVIEW.md) → [`04_DATABASE_SCHEMA`](04_DATABASE_SCHEMA.md)
> → the ADRs → the phase plans.

---

## 1. Core specifications (numbered, canonical)

These are the authoritative design documents. When something conflicts elsewhere, these win.

| Doc | What it covers |
|-----|----------------|
| [`01_PRODUCT_VISION.md`](01_PRODUCT_VISION.md) | Mission, guiding principles, what the product is and is not. |
| [`02_TECHNICAL_ARCHITECTURE.md`](02_TECHNICAL_ARCHITECTURE.md) | Full technical architecture specification. **Canonical** architecture doc. |
| [`03_CLAUDE_DEVELOPMENT_RULES.md`](03_CLAUDE_DEVELOPMENT_RULES.md) | Rationale behind the rules in the root [`CLAUDE.md`](../CLAUDE.md). |
| [`04_DATABASE_SCHEMA.md`](04_DATABASE_SCHEMA.md) | Tables, relationships, and the knowledge-graph schema. |
| [`05_PROMPT_LIBRARY.md`](05_PROMPT_LIBRARY.md) | Prompt design and the YAML prompt catalog (`backend/prompts/`). |
| [`06_RAG_DESIGN.md`](06_RAG_DESIGN.md) | Retrieval-augmented generation: collections, embedding, reranking. |
| [`07_PLUGIN_ORCHESTRATION.md`](07_PLUGIN_ORCHESTRATION.md) | The per-feature workflow checklist (the "definition of done"). |
| [`08_ROADMAP.md`](08_ROADMAP.md) | The build phases and their acceptance criteria (see the numbering caveat at its top). |
| [`09_DESIGN_GUIDELINES.css`](09_DESIGN_GUIDELINES.css) | Frontend visual design tokens / guidelines (CSS). |

---

## 2. Operational guides

Practical how-to docs for setting up and running the system.

| Doc | When to read it |
|-----|-----------------|
| [`ARCHITECTURE_OVERVIEW.md`](ARCHITECTURE_OVERVIEW.md) | A readable tour of the system layers — start here for orientation. |
| [`MODEL_SETUP.md`](MODEL_SETUP.md) | Installing Ollama and pulling `qwen3:8b` / `nomic-embed-text`. |
| [`DATA_IMPORT.md`](DATA_IMPORT.md) | Importing your résumés, job descriptions, projects, and GitHub repos. |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Day-to-day usage of the application. |
| [`OPTIMIZATION_SYSTEM.md`](OPTIMIZATION_SYSTEM.md) | The controlled autonomous optimization loop. |
| [`PACKAGING.md`](PACKAGING.md) | Building the macOS DMG + signing/notarization (Phase 13). |
| [`VERSIONING.md`](VERSIONING.md) | App-version single-source, `/health/version`, seeded-reproducibility spine (Phase 14.1). |
| [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | Common problems and fixes. |

### Engine specs & operational logs

| Doc | What it covers |
|-----|----------------|
| [`RESUME_ENGINE_SPEC.md`](RESUME_ENGINE_SPEC.md) | Resume engine pipeline (scoring → selection → layout → rewrite). |
| [`COVER_LETTER_ENGINE_SPEC.md`](COVER_LETTER_ENGINE_SPEC.md) | Cover-letter generation + voice modeling. |
| [`FRONTEND_DESIGN_SYSTEM.md`](FRONTEND_DESIGN_SYSTEM.md) | Phase 11 design system: tokens, motion, capability tiers. |
| [`PERFORMANCE_LOG.md`](PERFORMANCE_LOG.md) | Running perf-gate audit log (FPS, bundle size, latency). |
| [`SECURITY_DEPENDENCIES.md`](SECURITY_DEPENDENCIES.md) | Dependency security posture. |
| [`DECISIONS.md`](DECISIONS.md) | Running log of non-ADR decisions. |
| [`CURRENT_SPRINT.md`](CURRENT_SPRINT.md) | Thin pointer to the current/next phase. |
| [`BACKLOG.md`](BACKLOG.md) | Bug/issue/idea intake → triage → **batched into phases**. The intake convention for all future fix work. |
| [`optimization/`](optimization/) | Perf/inference/architecture spike findings + the deferred-optimization backlog. |
| [`v1/KNOWN_ISSUES.md`](v1/KNOWN_ISSUES.md) | Known issues (historical, Phase 8.1 era) — frozen under `v1/`. |

---

## 3. Architecture Decision Records (`adr/`)

The *why* behind each locked technology choice. ADRs are immutable history — supersede,
don't edit.

| ADR | Decision |
|-----|----------|
| [ADR-001](adr/ADR-001-local-first-architecture.md) | Local-first architecture (no cloud dependency at runtime). |
| [ADR-002](adr/ADR-002-sqlite-primary-database.md) | SQLite as the primary relational database. |
| [ADR-003](adr/ADR-003-chromadb-vector-store.md) | ChromaDB for vector storage and semantic search. |
| [ADR-004](adr/ADR-004-ollama-qwen3-llm.md) | Ollama + Qwen3 8B as the local LLM provider. |
| [ADR-005](adr/ADR-005-tauri-react-frontend.md) | Tauri + React + TypeScript for the desktop frontend. |
| [ADR-006](adr/ADR-006-evidence-confidence-system.md) | Evidence-based confidence system for all generated content. |
| [ADR-007](adr/ADR-007-fastapi-backend.md) | FastAPI as the backend framework. |
| [ADR-008](adr/ADR-008-multi-tenant-isolation.md) | Session-layer multi-tenant isolation (`X-Tenant-Id` unauthenticated selector; authn deferred). |
| [ADR-009](adr/ADR-009-privacy-preserving-aggregation.md) | Privacy-preserving cross-tenant aggregation — k-anonymity, content-free, no network. |
| [ADR-010](adr/ADR-010-autonomous-prompt-proposal-never-promote.md) | Autonomous prompt-proposal loop — propose-only, **never promotes** (human gate intact). |
| [ADR-011](adr/ADR-011-background-auto-update-network-boundary.md) | Background auto-update — one signed, TLS-only, data-free network channel. |
| [ADR-012](adr/ADR-012-controlled-autonomy-boundary.md) | Controlled-autonomy boundary — the agent recommends/generates/simulates but **never acts**; no outbound-action code path (enforced by a scan test). |
| [ADR-013](adr/ADR-013-plugin-ecosystem-cloud-scope.md) | Plugin/ecosystem/cloud scope — defer runtime-plugin engine, cloud sync, API exposure; opt-in at-rest encryption (off by default). |
| [ADR-014](adr/ADR-014-authentication-keychain-sessions.md) | Real authentication — keychain-backed per-user sessions (**supersedes ADR-008**). *Proposed (Phase 16).* |
| [ADR-015](adr/ADR-015-local-encryption-key-management.md) | Local encryption key mgmt + scope — Keychain + passphrase-KDF, default off (**extends ADR-013**). *Proposed (Phase 16).* |
| [ADR-016](adr/ADR-016-audit-log-tamper-evidence.md) | Audit log — tamper-evident hash chain, user-owned, configurable strictness. *Proposed (Phase 16).* |
| [ADR-017](adr/ADR-017-prompt-injection-defense.md) | Prompt-injection defense — layered (heuristic→classifier→LLM), two checkpoints, flag-over-block. *Proposed (Phase 16).* |
| [ADR-018](adr/ADR-018-plugin-permission-model.md) | Plugin permission model — capability manifest, default-closed, no full access (**amends ADR-013**). *Proposed (Phase 16).* |
| [ADR-019](adr/ADR-019-browser-extension-backend-bridge.md) | Browser-extension ↔ backend bridge — one-time token, localhost-only, app-gated, explicit-capture-only. *Proposed (Phase 17).* |
| [ADR-020](adr/ADR-020-alpha-distribution-update-rollout.md) | Alpha distribution + update channel + feature-flag rollout — unsigned-mac alpha, check-never-push, local A/B. *Proposed (Phase 18).* |

> ADRs 014–020 are **Proposed** (drafted during Phase 16–18 planning); each is ratified to
> **Accepted** when its phase builds. See the phase roadmaps under `superpowers/plans/`.

---

## 4. Implementation plans

**v1 is Phases 0–18.** Plans split by status:

- **Frozen v1 history → [`v1/plans/`](v1/plans/).** Completed phases 0–15 (roadmaps,
  segment-prompts, and the older `archive/` for 0–10). Frozen — read for history, not edited.
  Design specs from that era are in [`v1/specs/`](v1/specs/).
- **Active v1 phases → [`superpowers/plans/`](superpowers/plans/).** The final v1 arc, **16–18**.
- **Forward / post-v1 → [`v2/`](v2/).** Emergent, adhoc — see [`v2/ROADMAP.md`](v2/ROADMAP.md)
  + [`v2/IDEAS.md`](v2/IDEAS.md). Bug/issue/idea intake that *cuts* future phases lives in
  [`BACKLOG.md`](BACKLOG.md).

Each phase from 11 on has a `*-roadmap.md` (themes + reconciliation + segment map) and a
`*-segment-prompts.md` (copy-one-block-per-session build prompts) — start at the roadmap.

**Active — final v1 arc (`superpowers/plans/`):**

| Phase | Status | Start here |
|-------|--------|-----------|
| 16 — Security · privacy · isolation | Planned | [`phase-16-roadmap.md`](superpowers/plans/phase-16-roadmap.md) + [`phase-16-segment-prompts.md`](superpowers/plans/phase-16-segment-prompts.md) |
| 17 — Browser extension · job capture | Planned | [`phase-17-roadmap.md`](superpowers/plans/phase-17-roadmap.md) + [`phase-17-segment-prompts.md`](superpowers/plans/phase-17-segment-prompts.md) |
| 18 — Alpha release · onboarding · distribution | Planned | [`phase-18-roadmap.md`](superpowers/plans/phase-18-roadmap.md) + [`phase-18-segment-prompts.md`](superpowers/plans/phase-18-segment-prompts.md) |

**Frozen — shipped v1 phases (`v1/plans/`):** phases 0–10 under `v1/plans/archive/`; phases
11–15 roadmaps + segment-prompts directly under `v1/plans/`. See that directory for the full set.

---

## 5. Root-level documents

These intentionally live at the repository root because tooling and `CLAUDE.md` reference
them by fixed path.

| File | Purpose |
|------|---------|
| [`../README.md`](../README.md) | Project overview, setup, and run instructions. |
| [`../REPO_MAP.md`](../REPO_MAP.md) | Annotated directory tree of the whole repo. |
| [`../CLAUDE.md`](../CLAUDE.md) | Non-negotiable development rules (enforced for all contributors). |
| [`../IMPLEMENTATION_ORDER.md`](../IMPLEMENTATION_ORDER.md) | The fixed order features are built in. |
| [`../GAMEPLAN.md`](../GAMEPLAN.md) | Original full architecture spec. ⚠️ **Historical** — overlaps with [`02_TECHNICAL_ARCHITECTURE.md`](02_TECHNICAL_ARCHITECTURE.md), which is the canonical version. Prefer `02_` for current architecture. |
