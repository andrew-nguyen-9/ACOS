# ACOS Development Roadmap

> **Status (2026-06-23): Phases 0–13 complete.** Next: Phase 14–15 (see
> [`superpowers/plans/phase-14-15-roadmap.md`](superpowers/plans/phase-14-15-roadmap.md)).
>
> **⚠️ Numbering caveat.** Phases 0–8 below describe the *original* feature-build order
> (mirrors [`../IMPLEMENTATION_ORDER.md`](../IMPLEMENTATION_ORDER.md): DB → ingestion → … →
> Copilot). Actual execution diverged and **renumbered** from Phase 8 onward (e.g. actual
> Phase 8 = controlled-autonomous optimization, 11 = frontend, 12 = velocity/flywheel/
> multi-tenant, 13 = surfacing/onboarding/packaging). The **canonical per-phase ledger** is
> `docs/superpowers/plans/` (phases 0–10 in `plans/archive/`) plus the "Phase 11+" /
> "Phase 13 outcomes" sections at the end of this file and `MEMORY.md`. Treat the early
> headers here as historical intent, the late sections + plans as what shipped.

## Guiding Principle

Build vertically, not horizontally. Each phase must produce a working, testable vertical
slice of the system. No phase begins until the prior phase's acceptance criteria pass.

---

## Phase 0: Bootstrap

**Goal:** Establish project structure, documentation, schema, and architectural contracts
before any business logic is written.

**Deliverables:**
- [x] `docs/01_PRODUCT_VISION.md`
- [x] `docs/02_TECHNICAL_ARCHITECTURE.md`
- [x] `docs/03_CLAUDE_DEVELOPMENT_RULES.md`
- [x] `docs/04_DATABASE_SCHEMA.md`
- [x] `docs/05_PROMPT_LIBRARY.md`
- [x] `docs/06_RAG_DESIGN.md`
- [x] `docs/07_PLUGIN_ORCHESTRATION.md`
- [x] `docs/08_ROADMAP.md`
- [x] `docs/adr/` — 7 Architecture Decision Records
- [x] `CLAUDE.md` — project-level development rules
- [x] Full directory scaffold
- [x] `docs/superpowers/plans/` — Phase 0 implementation plan

**Acceptance Criteria:**
- All 8 docs exist and are complete
- All ADRs documented
- Directory structure matches `02_TECHNICAL_ARCHITECTURE.md`
- No business logic exists yet

---

## Phase 1: Foundation — Database & Knowledge Graph

**Goal:** Establish SQLite schema, SQLAlchemy models, Alembic migrations, and the
knowledge graph service. Seed the database with existing static profile data.

**Duration estimate:** 3–5 sessions

**Plugins required:** `context7` (SQLAlchemy, Alembic), `superpowers:test-driven-development`

**Deliverables:**
- SQLAlchemy models for all tables in `04_DATABASE_SCHEMA.md`
- Alembic migration files
- Repository layer (CRUD for each entity)
- Knowledge Graph service (node/edge CRUD + traversal)
- Seed script for existing `.static_files/profile/` data
- Unit tests: ≥90% coverage on all models and repositories
- FastAPI app skeleton with health check endpoint

**Key files:**
```
backend/models/                    (SQLAlchemy declarative models)
backend/repositories/              (data access layer)
backend/services/knowledge_graph/  (KG business logic)
database/migrations/               (Alembic files)
scripts/seed/seed_profile.py       (seed from .static_files)
backend/tests/unit/test_models/
backend/tests/unit/test_repositories/
```

**Acceptance Criteria:**
- All migrations run cleanly on fresh SQLite file
- All CRUD operations tested and passing
- `scripts/seed/seed_profile.py` loads `resume.txt`, `experience-bank.md`, `cv.txt` into DB
- `GET /health` returns `{"status": "ok", "db": "connected"}`
- 90%+ test coverage

---

## Phase 2: Document Ingestion Pipeline

**Goal:** Ingest all existing `.static_files/` documents into the knowledge graph.
Support PDF, DOCX, TXT, Markdown.

**Duration estimate:** 3–4 sessions

**Plugins required:** `security-review`, `context7` (pypdf, python-docx), `hookify`

**Deliverables:**
- File parser for PDF, DOCX, TXT, Markdown
- Ingestion pipeline: parse → normalize → extract entities → store
- Folder watcher (hookify) for auto-ingestion
- Entity extraction service (experiences, skills, projects from raw text)
- Duplicate detection via SHA-256 checksum
- Ingestion log table populated correctly
- Unit tests for each parser
- Integration test: end-to-end ingestion of a sample resume

**Key files:**
```
backend/ingestion/parsers/pdf.py
backend/ingestion/parsers/docx.py
backend/ingestion/parsers/txt.py
backend/ingestion/parsers/markdown.py
backend/ingestion/pipeline.py
backend/ingestion/entity_extractor.py
backend/services/ingestion/
backend/api/v1/routes/ingestion.py
scripts/ingestion/ingest_static_files.py
```

**Acceptance Criteria:**
- All `.static_files/` documents ingest without errors
- No duplicate records for same checksum
- Entity extraction populates experiences, projects, skills tables
- `POST /api/v1/ingest` accepts file upload and returns ingestion status
- Security: path traversal impossible, file size limits enforced

---

## Phase 3: Embeddings & ChromaDB

**Goal:** Embed all knowledge graph content into ChromaDB. Stand up the RAG
retrieval pipeline.

**Duration estimate:** 2–3 sessions

**Plugins required:** `context7` (ChromaDB, Ollama), `compound-engineering:ce-performance-reviewer`

**Deliverables:**
- Ollama embedding client (`nomic-embed-text`)
- ChromaDB client and collection manager
- Embedding pipeline for all collections defined in `06_RAG_DESIGN.md`
- Retrieval service: query → embed → multi-collection search → rerank → return
- Re-indexing script triggered every 5 applications
- Unit tests: retrieval returns expected documents for known queries
- Integration test: full RAG pipeline end-to-end

**Key files:**
```
backend/rag/embedder.py
backend/rag/chroma_client.py
backend/rag/collections.py
backend/rag/retriever.py
backend/rag/reranker.py
scripts/maintenance/reindex_all.py
backend/tests/integration/test_rag_pipeline.py
```

**Acceptance Criteria:**
- All 10 ChromaDB collections created and populated
- Similarity search returns plausible results for test queries
- Confidence metadata preserved in retrieved results
- `POST /api/v1/rag/query` returns ranked evidence with metadata

---

## Phase 4: Resume Engine

**Goal:** Generate tailored, ATS-optimized one-page resumes from the knowledge graph.

**Duration estimate:** 4–5 sessions

**Plugins required:** `feature-dev:feature-dev`, `playground`, `context7` (python-docx)

**Deliverables:**
- Resume generation service (JD → keywords → match → generate → ATS score → DOCX)
- ATS scoring engine (keyword, skill, experience, industry, education weights)
- DOCX export using `python-docx` templates
- Resume template storage and selection
- API routes: `POST /api/v1/resume/generate`, `POST /api/v1/resume/analyze-ats`
- Prompts: `resume/generate.yaml`, `resume/score_ats.yaml`, `resume/extract_keywords.yaml`
- Unit tests: ATS scoring, keyword extraction, bullet selection
- Integration test: full generate-and-export for a sample JD

**Key files:**
```
backend/services/resume/generator.py
backend/services/resume/ats_scorer.py
backend/services/ats/keyword_extractor.py
backend/services/resume/docx_exporter.py
backend/api/v1/routes/resume.py
backend/prompts/resume/generate.yaml
backend/prompts/resume/score_ats.yaml
backend/prompts/ats/analyze.yaml
```

**Acceptance Criteria:**
- Resume generated for 3 sample JDs from `.static_files/`
- Output is exactly one page
- No invented metrics, employers, or certifications
- ATS score within ±5 points of manual assessment
- DOCX opens correctly in Word and Google Docs
- All bullets traceable to source evidence

---

## Phase 5: Cover Letter Engine

**Goal:** Generate personalized cover letters that match Andrew's voice and structure.

**Duration estimate:** 2–3 sessions

**Plugins required:** `feature-dev:feature-dev`, `ralph-loop`

**Deliverables:**
- Voice learning service (learn writing profile from historical cover letters)
- Cover letter generation service
- Length variants: 100, 250, 400, full-page, custom
- DOCX + TXT export
- API routes: `POST /api/v1/cover-letter/generate`, `POST /api/v1/cover-letter/learn-voice`
- Prompts: `cover_letter/generate.yaml`, `cover_letter/learn_voice.yaml`

**Acceptance Criteria:**
- Voice profile extracted from all `.static_files/cover-letters/` documents
- Generated cover letter passes tone check (matches voice profile)
- Length within ±15 words of target

---

## Phase 6: Q&A Engine

**Goal:** Generate and manage application question answers.

**Duration estimate:** 2–3 sessions

**Plugins required:** `feature-dev:feature-dev`, `skill-creator`, `ralph-skills`

**Deliverables:**
- Question bank (import from `.static_files/` answer files)
- Answer generation: short / medium / long
- Variable substitution for `{{company}}`, `{{position}}`, etc.
- Answer edit tracking (original → edited → diff)
- API routes: CRUD for questions and answers
- Prompts: `questions/generate_bank.yaml`, `questions/answer_*.yaml`

**Acceptance Criteria:**
- All existing `.static_files/job-descriptions/*/application-answers.md` imported
- New answer for any question generated in <30 seconds
- Edit diff stored and used for future retrieval improvement

---

## Phase 7: Application CRM

**Goal:** Track the full application lifecycle from draft to outcome.

**Duration estimate:** 2–3 sessions

**Plugins required:** `feature-dev:feature-dev`

**Deliverables:**
- Application CRUD API
- Status pipeline: draft → applied → phone_screen → interview → final_round → offer/rejected
- Timeline event logging
- Outcome signal recording
- Recruiter tracking
- API: full CRUD at `/api/v1/applications`

**Acceptance Criteria:**
- All existing applications from `.static_files/job-descriptions/*/meta.json` imported
- Status transitions logged correctly
- Outcome signals written after every status change

---

## Phase 8: Career Copilot

**Goal:** RAG-powered chat assistant that answers career questions with evidence.

**Duration estimate:** 4–5 sessions

**Plugins required:** `agent-sdk-dev`, `feature-dev:feature-dev`, `compound-engineering:ce-agent-native-architecture`

**Deliverables:**
- Intent router
- Multi-collection RAG retriever
- Response generator with evidence panel
- Confidence assignment
- Streaming response support (SSE)
- API: `POST /api/v1/copilot/chat`
- Prompt: `copilot/route_intent.yaml`, `copilot/retrieve_and_respond.yaml`

**Acceptance Criteria:**
- "What are my strongest data engineering experiences?" returns ≥3 verified evidence items
- "Write a STAR answer for conflict resolution" generates a grounded response
- Responses never invent information not in the knowledge graph
- Evidence panel links to source records

---

## Phase 9: Learning Engine

**Goal:** Improve retrieval and ranking from outcome signals.

**Duration estimate:** 2–3 sessions

**Plugins required:** `ralph-loop`, `compound-engineering:ce-performance-reviewer`

**Deliverables:**
- Outcome signal processor
- Re-ranking weight updater
- Re-indexing scheduler (trigger every 5 applications)
- Analytics endpoint: `GET /api/v1/analytics/outcomes`

**Acceptance Criteria:**
- Experiences/projects associated with interview outcomes ranked higher
- Re-indexing completes in <5 minutes for full dataset
- `GET /api/v1/analytics/outcomes` returns signal breakdown by outcome type

---

## Phase 10: Intelligence Layer Upgrade

**Goal:** Upgrade ACOS from retrieval-and-generation to evidence-reasoning. Eliminate weak-confidence outputs via multi-stage RAG, context memory, reasoning traces, and self-correction.

**Duration estimate:** 3–4 sessions

**Plugins required:** `context7` (ChromaDB, FastAPI), `compound-engineering:ce-performance-reviewer`, `ralph-loop`

**Plan:** `docs/superpowers/plans/2026-06-21-phase-10-intelligence-layer-upgrade.md`

**Modules:**
1. Query Understanding — extract role_type, seniority, skills, 3 query vectors from JD
2. Multi-Vector Retrieval — parallel ChromaDB queries + recency-weighted SQL; MMR diversity merge
3. Evidence Ranking — relevance × confidence × dimension-coverage × recency scoring
4. Context Memory — short-term (session) + long-term (SQLite) + role/company ChromaDB memory
5. Reasoning Layer — reason-then-write: job match reasoning trace → grounded generation
6. Model Orchestration — route to fast_retrieval / deep_reasoning / ats_optimization / copilot modes
7. Embedding Intelligence — semantic chunking, skill normalization, project-to-skill expansion, 5 dimension collections
8. Self-Correction — auto-rewrite bullets < 3.0/5.0 score; flag hallucinations; deduplicate experiences

**Acceptance Criteria:**
- Bullets never truncate mid-phrase (≤40 words, ≤175 chars)
- DOCX output uses correct visual template per template_name (✅ delivered in pre-phase fixes)
- Reasoning trace cites only evidence IDs passed in context — no hallucinated references
- Self-corrector catches and rewrites all bullets > 175 chars
- Memory injection improves ATS score on second generation for same role
- ≥90% test coverage on all 8 new service modules
- No external API calls — Ollama only

---

## Phase 11: Frontend (Tauri + React) — ✅ COMPLETE

**Status:** ✅ **DONE** (2026-06-22). Delivered as an expanded two-track phase —
**backend production hardening (11.0–11.4)** + **showcase-grade frontend revamp
(11.5–11.9)** — under one shared, performance-gated constraint. Segment specs live in
`docs/superpowers/plans/2026-06-21-phase-11-*`; the index is `…-phase-11-roadmap.md`.

**Goal:** Production desktop UI for all engines.

**Duration estimate:** 6–8 sessions

**Plugins required:** `frontend-design`, `figma`, `context7` (React, Tauri), `compound-engineering:ce-design-implementation-reviewer`

**Pages:**
1. Dashboard — metrics, recent activity, ATS trends
2. Resume Builder — generate, preview, edit, export
3. Cover Letter Builder — generate, edit, export
4. Question Bank — import, generate, edit, categorize
5. Career Copilot — chat, evidence panel, confidence indicators
6. Application CRM — kanban pipeline, detail view
7. Knowledge Graph — document list, ingestion status, skill graph
8. Settings — model config, paths, API keys (none needed)

**Acceptance Criteria:**
- All pages functional with real backend ✅
- Playwright E2E tests pass for all golden paths ✅
- Tauri app builds to DMG on macOS — deferred to Phase 12 (packaging)
- No layout shifts or loading flashes ✅ (CLS 0.00 across traces)

**Phase 11 expanded criteria (all met):**
- Perf budget harness (11.0) + every later segment proven within budget
  (`docs/PERFORMANCE_LOG.md` close-out table) ✅
- Fault tolerance, data integrity, prompt-version locking, observability,
  controlled maintenance + backup/recovery (11.1–11.4) ✅
- Design system + motion + kinematics + WebGL materials + deep macOS integration +
  showcase capstones (11.5–11.9), all capability-gated + reduced-motion-degradable ✅
- BLOCKING 60 FPS gates passed; entry bundle 79.60 kB gz ≤ 80.8 ceiling ✅
- a11y / Off-tier sweep; phase-wide release-safety review ✅

---

## Phase 12: Packaging & Release

**Goal:** Ship a distributable macOS application.

**Duration estimate:** 1–2 sessions

**Deliverables:**
- DMG build via `tauri build`
- Bundled Ollama model check / first-run setup wizard
- Auto-update scaffold
- Release notes

> **Note:** Phase 12 pivoted from packaging to a Velocity / Flywheel / Multi-Tenant
> program (packaging moves to a later phase). Outcomes below.

### Phase 12 (Velocity / Flywheel / Multi-Tenant) — segment outcomes

**Shipped**
- 12.0–12.7 — velocity track: perf harness, SQLite pragmas, async runtime, cold-start,
  SSE streaming + cancellation, Ollama calibration, RAG throughput (consolidated Chroma +
  background ingest), FTS5 lexical leg (rank-bm25 dropped).
- 12.8 Spike A — Ollama structured output (`format`=JSON-Schema), flagged default-off.
- 12.10 — local feedback-loop engine (signals + rollups + explain).
- 12.11 — skill ROI engine (effect-size + n + ADR-006 confidence; explainable; golden).
- 12.14 — tenant isolation framework (one DB, enforced `tenant_id`, central guard across
  SQLite/Chroma/FTS5; **ADR-008**).
- 12.12 — resume strategy intelligence (ROI + signals + JD → personalized, evidence-grounded recs).
- 12.13 — adaptive prompt evolution (versioned, reversible, approval-gated; extends 11.2).
- 12.15 — privacy-preserving global aggregation (k-anonymity gate, content-free store; **ADR-009**).

**Deferred / rejected (documented, not dropped)**
- 12.8 Spikes B (logit_bias) + C (speculative decoding) — NO-GO; absent from Ollama API
  (see `docs/optimization/inference-spike-findings.md`).
- 12.9 — six architecture spikes, **all defer/reject, 0 adopts** → production stack
  unchanged (see `docs/optimization/architecture-spike-findings.md` +
  `deferred-optimization-backlog.md` with measured reopen conditions).
- Live-Ollama benches (TTFT, structured-output) verified at their segment commits; not
  re-run at close-out (no live Ollama in the close-out environment).

**New tables:** `signals` (12.10), `tenants` + `tenant_id` FK across owned tables (12.14),
`global_patterns` (12.15). 12.13 extends existing `prompt_versions` (no new table).
**ADRs:** ADR-008 (tenant isolation), ADR-009 (privacy-preserving aggregation) — both Accepted.

---

## Milestone Summary

| Milestone | Phase | Criteria |
|-----------|-------|---------|
| M0: Foundation | 0–1 | DB running, seed data loaded, all models tested |
| M1: Knowledge | 2–3 | All static files ingested, ChromaDB populated |
| M2: Generation | 4–5 | Resume + cover letter generated for 3 JDs |
| M3: Full Backend | 6–9 | All API endpoints operational |
| M3.5: Intelligence | 10 | Reasoning layer, memory, self-correction operational |
| M4: Desktop App | 11 | All UI pages functional |
| M5: Ship | 12 | DMG builds, installs, runs offline |

---

## Phase 13 outcomes — surfacing, onboarding, packaging, automation (2026-06-23)

Phase 13 surfaced the headless Phase-12 flywheel, finished onboarding, reclaimed the
displaced M5 packaging, and added approval-gated automation.

| Segment | Outcome | Status |
|---------|---------|--------|
| 13.0–13.4 | Flywheel data layer + skill-ROI / strategy / global-pattern surfaces + prompt-review queue (ADR-009/010) | Shipped |
| 13.5 | Onboarding doc-upload → skill/Career-Voice surfacing, synthetic clearly labeled (no cold-start engine; 12.3 was the warmup skeleton) | Shipped |
| 13.6 | Autonomous prompt-proposal loop — **propose-only, never promotes** (ADR-010) | Shipped |
| 13.7 | Consent-gated first-run model pull with progress + degraded fallback | Shipped |
| 13.8 | macOS DMG: signing/notarization config + build script + `PACKAGING.md` | **Configured, not release-verified** (needs cert + release machine) |
| 13.9 | Signed background auto-update + release notes (ADR-011) | Shipped — **single deliberate network channel** |
| 13.10 | Verification debt: scored golden-set + k-anon demo fixture + live-bench gate | Shipped; deferred-opt items all stay **VOID** (no reopen number fired) |

**Deferred (not in Phase 13):** multi-profile UI (substrate only), Chroma per-tenant
read-filter, real authentication, Windows/Linux packaging, and the four VOID
optimization-backlog items. **Network boundary changed:** ACOS is no longer strictly
no-network — one signed, TLS-only, data-free update channel exists (ADR-011); ADR-008's
deferred-authn note is now load-bearing.

---

## Backlog (Post-Phase-11)

### Deferred optimizations (Phases 13–18)

Phase 12.9 measured six architecture candidates and deferred/rejected all six. They are registered with
their measured reopen conditions in **`docs/optimization/deferred-optimization-backlog.md`** — Phases 13–18
consult that file before re-litigating any of them. Reopen only when the candidate's measured condition
fires (msgpack IPC, FAISS vector backend, Nuitka packaging, pinned memory; PyO3 escalates to a Phase 13 epic).

### Other

- Windows and Linux packaging
- GitHub Actions CI pipeline
- LinkedIn scraper integration
- Indeed / Glassdoor JD import
- PMP certification tracking module
- Interview recording transcription
- Automated ATS submission testing
- Multi-user / family account support
- Mobile companion app (iOS)
