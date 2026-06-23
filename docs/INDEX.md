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
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Known issues (historical, Phase 8.1 era). |
| [`CURRENT_SPRINT.md`](CURRENT_SPRINT.md) | Thin pointer to the current/next phase. |
| [`optimization/`](optimization/) | Perf/inference/architecture spike findings + the deferred-optimization backlog. |

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

---

## 4. Implementation plans (`superpowers/plans/`)

One plan per build phase, in execution order. Phases 0–10 are in `plans/archive/`. From
Phase 11 on, each phase has a `*-roadmap.md` (themes + segment map) and, for 12–15, a
`*-segment-prompts.md` (copy-one-block-per-session build prompts) — start there.

**Completed phases (`plans/archive/`):**

| Phase | Plan |
|-------|------|
| 0 — Bootstrap | [`archive/2026-06-18-phase-0-bootstrap.md`](superpowers/plans/archive/2026-06-18-phase-0-bootstrap.md) |
| 1 — Foundation (DB + KG) | [`archive/2026-06-18-phase-1-foundation.md`](superpowers/plans/archive/2026-06-18-phase-1-foundation.md) |
| 2 — Intelligence layer | [`archive/2026-06-18-phase-2-intelligence-layer.md`](superpowers/plans/archive/2026-06-18-phase-2-intelligence-layer.md) |
| 3 — Document generation | [`archive/2026-06-18-phase-3-document-generation.md`](superpowers/plans/archive/2026-06-18-phase-3-document-generation.md) |
| 4 — Intelligence interaction | [`archive/2026-06-18-phase-4-intelligence-interaction.md`](superpowers/plans/archive/2026-06-18-phase-4-intelligence-interaction.md) |
| 5 — Productization | [`archive/2026-06-19-phase-5-productization.md`](superpowers/plans/archive/2026-06-19-phase-5-productization.md) · [`ui`](superpowers/plans/archive/2026-06-19-phase-5-ui-productization.md) |
| 6 — Reliability, testing, security | [`archive/2026-06-19-phase-6-reliability-testing-security.md`](superpowers/plans/archive/2026-06-19-phase-6-reliability-testing-security.md) |
| 7 — Production packaging & release | [`archive/2026-06-19-phase-7-production-packaging-release.md`](superpowers/plans/archive/2026-06-19-phase-7-production-packaging-release.md) |
| 8 — Controlled autonomous optimization | [`archive/2026-06-20-phase-8-controlled-autonomous-optimization.md`](superpowers/plans/archive/2026-06-20-phase-8-controlled-autonomous-optimization.md) |
| 8.1 — Engine revamp | [`archive/2026-06-20-phase-8-1-engine-revamp.md`](superpowers/plans/archive/2026-06-20-phase-8-1-engine-revamp.md) |
| 9 — Career simulation & strategy | [`archive/2026-06-20-phase-9-career-simulation-strategy-engine.md`](superpowers/plans/archive/2026-06-20-phase-9-career-simulation-strategy-engine.md) |
| 10 — Intelligence layer upgrade | [`archive/2026-06-21-phase-10-intelligence-layer-upgrade.md`](superpowers/plans/archive/2026-06-21-phase-10-intelligence-layer-upgrade.md) |

**Phases 11–13 (`plans/`):** each has a roadmap + per-segment plans:

| Phase | Start here |
|-------|-----------|
| 11 — Hardening + frontend revamp | [`2026-06-21-phase-11-roadmap.md`](superpowers/plans/2026-06-21-phase-11-roadmap.md) (+ `phase-11-0…11-9`) |
| 12 — Velocity · flywheel · multi-tenant | [`2026-06-22-phase-12-roadmap.md`](superpowers/plans/2026-06-22-phase-12-roadmap.md) + [`segment-prompts`](superpowers/plans/phase-12-segment-prompts-11-16.md) (+ `phase-12-0…12-16`) |
| 13 — Surfacing · onboarding · packaging | [`phase-13-roadmap.md`](superpowers/plans/phase-13-roadmap.md) + [`phase-13-segment-prompts.md`](superpowers/plans/phase-13-segment-prompts.md) |

**Phases 14–15 (planned, not started):**

| Phase | Start here |
|-------|-----------|
| 14–15 — Hardening + controlled autonomous agent | [`phase-14-15-roadmap.md`](superpowers/plans/phase-14-15-roadmap.md) + [`phase-14-15-segment-prompts.md`](superpowers/plans/phase-14-15-segment-prompts.md) |

Design specs produced during brainstorming live alongside these under
`superpowers/specs/` (created as needed).

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
