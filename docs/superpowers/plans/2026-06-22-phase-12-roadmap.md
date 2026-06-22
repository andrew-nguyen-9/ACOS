# Phase 12 — Velocity + Career Intelligence Flywheel + Multi-Tenant (Roadmap Index)

**Status:** Planned (no segment implemented yet)
**Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Created:** 2026-06-22
**Owner:** Andrew Nguyen (`andrew-nguyen-9`)

---

## Purpose

Phase 12 has three tracks plus a workflow track:

1. **Velocity (backend optimization)** — push the Tauri → FastAPI → SQLite/Chroma → Ollama
   stack toward millisecond latency budgets on Apple Silicon: async I/O, streaming, cold-start,
   Ollama TTFT/memory calibration, RAG throughput.
2. **Career Intelligence Flywheel** — turn outcomes into compounding intelligence: a local
   feedback loop, a skill-ROI engine, resume-strategy intelligence, and adaptive prompt evolution.
3. **Multi-Tenant Generalization Layer** — isolate per-user data into tenants, and learn
   *anonymized, aggregate* patterns across tenants without leaking any raw or personal data.
4. **Token-efficient workflow** — Phase 12 dev runs under Caveman + Ponytail + RTK + Superpowers
   to minimize token spend per segment (set up in 12.0).

**Shared constraint (inherited from Phase 11):** *Performance is never sacrificed for show, and
stability > optimization.* Segment 12.0 extends the perf harness; every later segment must prove
(via that harness) it did not regress startup time, request latency, frame rate, or bundle size.

This file is the **index**. Each segment has its own self-contained spec in this directory. A
fresh session should be able to open a single segment spec and start work with minimal archaeology.

---

## How to use this roadmap (for future sessions)

1. Confirm the prior segment's **Definition of Done** is met (each spec lists it).
2. Open the target segment spec (`2026-06-22-phase-12-N-*.md`).
3. Follow its file-level plan + test plan. **TDD: tests before implementation** (CLAUDE.md rule 2).
4. Run the perf harness before and after; attach the delta to the PR.
5. Use the plugin orchestration checklist in each spec (CLAUDE.md rule 5) and `context7` for any
   framework API (CLAUDE.md rule 4 — uvloop, aiosqlite, FastAPI streaming, Chroma, Ollama, FTS5).

**Global rules that apply to every segment:**
- No hallucination; confidence system intact (CLAUDE.md non-negotiables).
- No autonomous destructive actions; learning/optimization that mutates prompts stays
  versioned + reversible (carry-over from Phase 11.2/11.4).
- **Local-first privacy is non-negotiable** (see "Privacy boundary" below).
- No new attribution in git artifacts (CLAUDE.md → Git Attribution).

---

## Segment map

| Seg | Title | Track | Spec file |
|-----|-------|-------|-----------|
| 12.0 | Foundation: perf harness + token-efficient workflow | Shared | `…-phase-12-0-foundation-velocity-harness.md` |
| 12.1 | SQLite hot-path pragmas (WAL / synchronous / mmap) | Velocity | `…-phase-12-1-sqlite-pragmas.md` |
| 12.2 | Async runtime (uvloop + aiosqlite + async sessions) | Velocity | `…-phase-12-2-async-runtime.md` |
| 12.3 | Cold-start (lazy imports + single-worker + sidecar warmup) | Velocity | `…-phase-12-3-cold-start.md` |
| 12.4 | SSE streaming + generation cancellation | Velocity | `…-phase-12-4-sse-streaming.md` |
| 12.5 | Ollama memory/TTFT calibration | Velocity | `…-phase-12-5-ollama-calibration.md` |
| 12.6 | RAG throughput (collections, batching, background ingest, pruning) | Velocity | `…-phase-12-6-rag-throughput.md` |
| 12.7 | FTS5 lexical search (replace Python BM25) | Velocity | `…-phase-12-7-fts5-lexical.md` |
| 12.8 | Advanced inference spikes (GBNF / logit bias / spec-decoding) — optional | Velocity | `…-phase-12-8-inference-spikes.md` |
| 12.9 | Architecture spikes (msgpack IPC / FAISS / PyO3 / Nuitka) — research | Velocity | `…-phase-12-9-architecture-spikes.md` |
| 12.10 | Local feedback-loop engine | Flywheel | `…-phase-12-10-local-feedback-loop.md` |
| 12.11 | Skill ROI engine | Flywheel | `…-phase-12-11-skill-roi-engine.md` |
| 12.12 | Resume strategy intelligence layer | Flywheel | `…-phase-12-12-resume-strategy-intelligence.md` |
| 12.13 | Adaptive prompt evolution | Flywheel | `…-phase-12-13-adaptive-prompt-evolution.md` |
| 12.14 | Tenant isolation framework | Multi-tenant | `…-phase-12-14-tenant-isolation.md` |
| 12.15 | Privacy-preserving global pattern + ROI aggregation | Multi-tenant | `…-phase-12-15-global-aggregation.md` |
| 12.16 | Phase 12 close-out (docs, audit, ADRs, review) | Shared | `…-phase-12-16-closeout.md` |

**Dependency order:**
- `12.0` first (gates everything; defines budgets).
- **Velocity track:** `12.1` → `12.2` → `12.3` → `12.4` → `12.5` → `12.6` → `12.7`. `12.8`/`12.9`
  are optional spikes, run only if their budget case is proven; do not block the flywheel.
- **Flywheel track:** `12.10` → `12.11` → `12.12` → `12.13` (sequential; each consumes the prior's signals).
- **Multi-tenant track:** `12.14` → `12.15`. `12.14` **must precede** any cross-tenant work in 12.15
  and ideally precedes the flywheel persistence (12.10) so flywheel data is tenant-scoped from day one.
- `12.16` last.

> **Recommended global order:** 12.0 → 12.1 → 12.2 → 12.3 → 12.14 (tenant scoping early) → 12.4 →
> 12.5 → 12.6 → 12.7 → 12.10 → 12.11 → 12.12 → 12.13 → 12.15 → (12.8/12.9 if justified) → 12.16.
> Rationale: ship cheap high-impact perf wins first, lay the tenant boundary before persisting any
> flywheel data, then build the flywheel on top of tenant-scoped storage.

---

## Performance budgets (carried from Phase 11.0; re-baseline in 12.0)

These remain the ceilings. 12.0 re-baselines on the current machine and adds new metrics for
the features Phase 12 introduces.

| Metric | Phase 11 budget ceiling | Phase 12 target | Measured by |
|--------|------------------------|-----------------|-------------|
| Backend cold start (import → ready), median | ≤ 778 ms | **≤ 400 ms** (lazy imports, 12.3) | `scripts/perf/startup_bench.py` |
| `POST /resume/generate` median (mocked LLM) | ≤ 0.35 ms | no regression | pytest-benchmark |
| Time-to-first-token (TTFT), live Ollama | — (new) | **≤ 800 ms** warm (12.4/12.5) | new bench in 12.0 |
| Document ingestion (per 5-page PDF), live | — (new) | **≤ 3 s** (batched embed, 12.6) | new bench in 12.0 |
| Frontend idle FPS | ≥ 60 | ≥ 60 | FPS meter dev overlay |
| Initial JS bundle (gzipped) | ≤ 80.8 kB | ≤ 80.8 kB | `vite build` report |

New-metric baselines need **live Ollama** and are gathered in 12.0; until then they are targets,
not gates. Any segment that would breach a ceiling must optimize until it fits or ship behind a
default-off flag and document the cost. No silent regressions.

---

## Privacy boundary (Multi-Tenant — read before 12.14/12.15)

CLAUDE.md security requirements state **"Local only: No data transmitted to external services
during operation."** The Phase 12 brief asks for *cross-user* global learning. These are reconciled
as follows, and this is binding for the whole multi-tenant track:

- **Tenant boundary is absolute.** No raw resume/cover-letter/profile content, no PII, and no
  per-tenant identifiers ever cross the tenant boundary.
- **Global layer sees only anonymized, aggregated patterns** — structural and statistical
  abstractions (e.g. "section ordering X correlates with higher ATS in industry Y"), computed with
  a **minimum aggregation threshold (k-anonymity, k ≥ 5 tenants)** before any pattern is emitted.
- **Cross-device / cross-install sharing is OUT OF SCOPE for Phase 12.** The global layer is built
  and exercised against multiple *local* tenants only. Any future network sync is **opt-in, off by
  default, and gated behind a new ADR** — it is not implemented here. This preserves local-first.
- A new **ADR-008 (multi-tenant isolation)** and **ADR-009 (privacy-preserving aggregation)** are
  written in 12.14/12.15 and ratified in 12.16.

If a future product decision wants real cross-install learning, that is a Phase 13 conversation
with its own threat model — not a silent expansion of Phase 12.

---

## Token-efficient development workflow (set up in 12.0)

Phase 12 is large; the dev loop is run to minimize Claude token spend per segment:

| Tool | Role in Phase 12 |
|------|------------------|
| **RTK** | CLI proxy; git/test/build commands routed through `rtk` for 60–90% output-token savings (hook-rewritten, transparent). |
| **Caveman** | Terse assistant output during implementation (code/commits stay normal prose). |
| **Ponytail** | Laziness ladder on every segment — stdlib/native/existing-dep before new code; mark deliberate simplifications with `ponytail:` comments. |
| **Superpowers** | `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review` enforced per segment. |
| `context7` | All framework APIs (uvloop/aiosqlite/FastAPI/Chroma/Ollama/FTS5) — never from memory (CLAUDE.md rule 4). |
| `ralph-loop` / `ralph-skills` | Flywheel track (12.10–12.13): optimization loop + skill-ROI modeling scaffolding. |
| `skill-creator` | Flywheel ontology expansion (skill taxonomy growth in 12.11/12.12). |

This is a *workflow* constraint, not product code — 12.0 documents it; later segments just follow it.

---

## Source material

- Phase 12 brief (backend optimization JSON + "additional features" + Ollama recs + Flywheel +
  Multi-Tenant) — in conversation history; the genuine, de-duplicated strategies are distributed
  across segment specs. The 40 `EPIC-ADV-*` epics in the brief are duplicates of two micro-opts
  (pinned unified memory; JIT reranking) — both folded into 12.9 as low-priority, measure-first items.
- Verified current state (probed 2026-06-22): DB is **synchronous** (`backend/database.py`,
  `create_engine`/`sessionmaker`); **no uvloop**; **no `StreamingResponse`**; `ollama_client` sets
  only `temperature`/`num_predict`; **10 Chroma collections** (`backend/rag/collections.py`); **no
  tenant/user model** (single-user) — multi-tenant is greenfield. WAL+FK pragmas already exist
  (Phase 11.1); 12.1 verifies and extends them.
- Existing architecture: `docs/02_TECHNICAL_ARCHITECTURE.md`, `docs/ARCHITECTURE_OVERVIEW.md`,
  `docs/06_RAG_DESIGN.md`, `docs/04_DATABASE_SCHEMA.md`, `docs/adr/`, `REPO_MAP.md`.

---

## Tech additions across Phase 12 (introduced lazily, per segment)

| Dependency | Segment | Why |
|------------|---------|-----|
| `uvloop` | 12.2 | Cython event loop |
| `aiosqlite` + SQLAlchemy async | 12.2 | Non-blocking DB |
| `sse-starlette` (or raw `StreamingResponse`) | 12.4 | Token streaming |
| SQLite **FTS5** (stdlib, no dep) | 12.7 | Native BM25 lexical search |
| `msgpack` *(spike)* | 12.9 | Compact IPC — only if measured win |
| `faiss-cpu` *(spike)* | 12.9 | Vector-store alternative evaluation |

No dependency is added without a `context7` check and a Ponytail ladder pass first. Spikes (12.8/12.9)
add nothing to the shipped binary unless their segment is explicitly accepted.
