# Phase 11 — Production Hardening + Frontend Revamp (Roadmap Index)

**Status:** Planned (no segment implemented yet)
**Branch:** `feat/phase-11-hardening-and-frontend`
**Created:** 2026-06-21
**Owner:** Andrew Nguyen (`andrew-nguyen-9`)

---

## Purpose

Phase 11 has two independent tracks that share one constraint:

1. **Backend production hardening** (11.1–11.4) — make ACOS run for years as a stable
   personal career OS without degradation, corruption, or architectural drift.
2. **Frontend revamp** (11.5–11.9) — an aggressive, showcase-grade macOS-native UI/UX
   built on hardware-accelerated, performance-gated principles.

**Shared constraint:** *Performance is never sacrificed for show.* Segment 11.0 builds the
measurement harness first; every later segment must prove (via that harness) it did not
regress startup time, request latency, or frame rate.

This file is the **index**. Each segment has its own self-contained spec in this directory.
A fresh Claude session should be able to open a single segment spec and start work with
minimal code archaeology.

---

## How to use this roadmap (for future sessions)

1. Confirm the prior segment's **Definition of Done** is met (each spec lists it).
2. Open the target segment spec (`2026-06-21-phase-11-N-*.md`).
3. Follow its file-level plan + test plan. TDD: tests before implementation (CLAUDE.md rule 2).
4. Run the perf harness (built in 11.0) before and after; attach results to the PR.
5. Use the plugin orchestration checklist in each spec (CLAUDE.md rule 5).

**Global rules that apply to every segment** (from the Phase 11 brief):
- No autonomous destructive actions. All maintenance/optimization requires explicit user approval.
- No self-modifying production changes.
- System stability > optimization.
- No hallucination; confidence system intact (CLAUDE.md non-negotiables).

---

## Segment map

| Seg | Title | Track | Spec file |
|-----|-------|-------|-----------|
| 11.0 | Foundation & Perf Budget Harness | Shared | `2026-06-21-phase-11-0-foundation-perf-harness.md` |
| 11.1 | Fault Tolerance + Data Integrity | Backend | `2026-06-21-phase-11-1-fault-tolerance-data-integrity.md` |
| 11.2 | Prompt Version Locking + Observability | Backend | `2026-06-21-phase-11-2-prompt-locking-observability.md` |
| 11.3 | Performance + Learning Stability | Backend | `2026-06-21-phase-11-3-performance-learning-stability.md` |
| 11.4 | Controlled Maintenance + Backup/Recovery | Backend | `2026-06-21-phase-11-4-maintenance-backup-recovery.md` |
| 11.5 | FE Foundation (design system + perf architecture) | Frontend | `2026-06-21-phase-11-5-fe-foundation.md` |
| 11.6 | FE Kinematics + State Perception | Frontend | `2026-06-21-phase-11-6-fe-kinematics-perception.md` |
| 11.7 | FE Hardware-Accelerated Materials (WebGL) | Frontend | `2026-06-21-phase-11-7-fe-hardware-materials.md` |
| 11.8 | FE Deep macOS Integration + Signature Features | Frontend | `2026-06-21-phase-11-8-fe-macos-integration-features.md` |
| 11.9 | FE Showcase Capstones + Close-out | Frontend | `2026-06-21-phase-11-9-fe-showcase-closeout.md` |

**Dependency order:** 11.0 → (11.1 → 11.2 → 11.3 → 11.4) and 11.0 → (11.5 → 11.6 → 11.7 → 11.8 → 11.9).
Backend and frontend tracks are independent after 11.0 and may be worked in either order,
but within each track segments are sequential.

---

## Performance budgets (defined in 11.0, enforced everywhere after)

These are the hard gates. Numbers were baselined in 11.0 on the dev machine
(`macOS-26.5.1-arm64`, Apple Silicon, Python 3.12.13) and stored in
`docs/PERFORMANCE_LOG.md`; the values below are the **ceilings** a segment may not exceed.
Baselines are machine-relative — re-baseline on a new machine before comparing.

| Metric | Baseline (2026-06-21) | Budget ceiling | Measured by |
|--------|----------------------|----------------|-------------|
| Backend cold start (import → ready), median | 707 ms | ≤ 778 ms (+10%) | `scripts/perf/startup_bench.py` |
| Backend cold start p95 | 1083 ms | ≤ 1191 ms (+10%) | `scripts/perf/startup_bench.py` |
| `POST /resume/generate` median (mocked LLM) | 0.32 ms | ≤ 0.35 ms (+10%) | pytest-benchmark |
| Copilot chat median (mocked LLM) | 0.008 ms | ≤ 0.009 ms (+10%) | pytest-benchmark |
| Frontend idle FPS | ≥ 60 (target 120 ProMotion) | ≥ 60 | FPS meter dev overlay |
| Frontend interaction jank (long tasks > 50ms) | 0 during animations | 0 | Chrome DevTools trace / Lighthouse |
| Initial JS bundle (gzipped) | 70.3 kB | ≤ 80.8 kB (+15% per heavy segment) | `vite build` report |

Any segment that would breach a budget must either (a) optimize until it fits, or
(b) ship the feature behind a default-off flag and document the cost. No silent regressions.

---

## Source material

- Phase 11 brief (production hardening) — in conversation history; mirrored in segment specs.
- Frontend guideline catalogs (Hardware-Accelerated Materials, Kinematic Motion, Variable
  Typography, Advanced State, Deep macOS Integration; Zero-Latency Perf Architecture; 2027
  Career Copilot feature catalog) — these are **principle sources, not checklists**. Each FE
  segment cites the specific guideline IDs it implements and explicitly lists what it drops.
- Existing architecture: `docs/02_TECHNICAL_ARCHITECTURE.md`, `docs/ARCHITECTURE_OVERVIEW.md`,
  `docs/adr/`, `docs/04_DATABASE_SCHEMA.md`.

---

## Tech additions across Phase 11 (introduced lazily, per segment)

| Dependency | Segment | Why |
|------------|---------|-----|
| `framer-motion` | 11.5 | Motion primitives, layout projection, scroll kinematics |
| `@tanstack/react-virtual` | 11.6 | List virtualization (DOM node ceiling) |
| `@react-three/fiber` + `three` | 11.7 | WebGL/shader materials |
| Custom Rust Tauri plugin (haptics) | 11.8 | Native macOS haptic feedback |

No backend runtime deps are added; hardening uses stdlib + existing SQLAlchemy/Alembic/Chroma.
