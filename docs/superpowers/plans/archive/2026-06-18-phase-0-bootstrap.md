# Phase 0: Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 0 bootstrap — all documentation, directory structure, ADRs, and project configuration exist before any business logic is written.

**Architecture:** Documentation-first. All architectural decisions are recorded in ADRs before implementation. Schema defined in SQL DDL before ORM models are written. Prompt contracts defined before LLM calls are made.

**Tech Stack:** No code yet — this plan creates the documentation scaffold that governs all future implementation.

## Global Constraints

- No business logic in Phase 0 — documentation and structure only
- All `docs/` files must be complete enough to guide a new engineer with zero context
- CLAUDE.md must be at project root
- ADRs must include alternatives-considered table
- Directory scaffold must match `02_TECHNICAL_ARCHITECTURE.md`
- Phase 0 is complete only when every checkbox below is checked

---

### Task 1: Repository Analysis

**Files:**
- Read: `GAMEPLAN.md`
- Read: `IMPLEMENTATION_ORDER.md`
- Read: `docs/01_PRODUCT_VISION.md`
- Read: `docs/02_TECHNICAL_ARCHITECTURE.md`
- Read: `docs/03_CLAUDE_DEVELOPMENT_RULES.md`
- Read: `.static_files/profile/resume.txt`
- Read: `.static_files/profile/positioning-and-strategy.md`

- [x] **Step 1: Audit existing files**

```bash
find . -type f | sort
```

Expected: Shows GAMEPLAN.md, IMPLEMENTATION_ORDER.md, 3 existing docs files, and `.static_files/` tree.

- [x] **Step 2: Read all existing documentation**

Understand user's background, existing architectural decisions, and what's missing from Phase 0.

- [x] **Step 3: Note gaps**

Missing: docs/04 through 08, all ADRs, CLAUDE.md, directory structure, ChromaDB collections, API contracts.

---

### Task 2: Directory Structure

**Files:**
- Create: `backend/` (with subdirectories per `02_TECHNICAL_ARCHITECTURE.md`)
- Create: `frontend/` (with subdirectories)
- Create: `database/migrations/`, `database/seed/`
- Create: `scripts/`, `tests/`, `examples/`
- Create: `docs/adr/`, `docs/superpowers/plans/`

- [x] **Step 1: Create all directories**

```bash
mkdir -p backend/{api/v1/{routes,schemas,dependencies},services/{knowledge_graph,ingestion,resume,cover_letter,ats,questions,copilot,learning},models,repositories,prompts/{resume,cover_letter,ats,copilot,questions,ingestion,ranking},rag,tests/{unit,integration}} frontend/{src/{pages,components/{ui,resume,cover_letter,copilot,applications,shared},hooks,services,stores,layouts,types,utils},public} database/{migrations,seed,backups} scripts/{ingestion,maintenance,seed} tests/{e2e,fixtures} examples/{job_descriptions,resumes,cover_letters} docs/{adr,superpowers/plans}
```

- [x] **Step 2: Add .gitkeep files**

```bash
find backend frontend database scripts tests examples -type d | while read d; do touch "$d/.gitkeep"; done
```

- [x] **Step 3: Verify structure**

```bash
find . -type d | grep -v .git | sort
```

Expected: All directories present matching architecture doc.

---

### Task 3: Core Documentation Files

**Files:**
- Create: `docs/04_DATABASE_SCHEMA.md`
- Create: `docs/05_PROMPT_LIBRARY.md`
- Create: `docs/06_RAG_DESIGN.md`
- Create: `docs/07_PLUGIN_ORCHESTRATION.md`
- Create: `docs/08_ROADMAP.md`

- [x] **Step 1: Write `04_DATABASE_SCHEMA.md`**

Full SQL DDL for all 18 tables, indexes, FK constraints, confidence level checks.

- [x] **Step 2: Write `05_PROMPT_LIBRARY.md`**

Prompt file format, full catalog (5 modules × N prompts), variable reference.

- [x] **Step 3: Write `06_RAG_DESIGN.md`**

Architecture diagram, ChromaDB collection definitions, chunking strategies, retrieval pipeline, re-ranking algorithm.

- [x] **Step 4: Write `07_PLUGIN_ORCHESTRATION.md`**

Feature lifecycle, plugin matrix by phase, context7 protocol, definition of done checklist.

- [x] **Step 5: Write `08_ROADMAP.md`**

11 phases, acceptance criteria per phase, milestone summary, backlog.

---

### Task 4: Architecture Decision Records

**Files:**
- Create: `docs/adr/ADR-001` through `ADR-007`

- [x] **Step 1: Write all 7 ADRs**

  - ADR-001: Local-first architecture
  - ADR-002: SQLite as primary database
  - ADR-003: ChromaDB for vector storage
  - ADR-004: Ollama + Qwen3 8B
  - ADR-005: Tauri + React frontend
  - ADR-006: Evidence-based confidence system
  - ADR-007: FastAPI backend

---

### Task 5: Project Configuration Files

**Files:**
- Create: `CLAUDE.md`
- Create: `docs/superpowers/plans/2026-06-18-phase-0-bootstrap.md` (this file)

- [x] **Step 1: Write CLAUDE.md**

Non-negotiable rules, tech stack table, file path reference, security requirements, testing requirements.

- [x] **Step 2: Write this plan file**

---

### Task 6: Verification

- [x] **Step 1: Verify all docs files exist**

```bash
ls docs/*.md docs/adr/*.md
```

Result: 8 docs files + 7 ADR files confirmed.

- [x] **Step 2: Verify directory structure**

```bash
find backend frontend database scripts tests examples -type d | wc -l
```

Result: 42 directories confirmed.

- [x] **Step 3: Verify CLAUDE.md exists at root**

```bash
ls -la CLAUDE.md
```

- [x] **Step 4: Commit Phase 0**

```bash
git add docs/ backend/ frontend/ database/ scripts/ tests/ examples/ CLAUDE.md
git commit -m "feat: Phase 0 bootstrap — documentation, schema, ADRs, directory structure"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Status |
|-------------|--------|
| `docs/01_PRODUCT_VISION.md` | ✅ Exists (from prior session) |
| `docs/02_TECHNICAL_ARCHITECTURE.md` | ✅ Exists (from prior session) |
| `docs/03_CLAUDE_DEVELOPMENT_RULES.md` | ✅ Exists (from prior session) |
| `docs/04_DATABASE_SCHEMA.md` | ✅ Created |
| `docs/05_PROMPT_LIBRARY.md` | ✅ Created |
| `docs/06_RAG_DESIGN.md` | ✅ Created |
| `docs/07_PLUGIN_ORCHESTRATION.md` | ✅ Created |
| `docs/08_ROADMAP.md` | ✅ Created |
| Repository structure | ✅ Created |
| ADRs (7) | ✅ Created |
| CLAUDE.md | ✅ Created |
| No business logic | ✅ Confirmed |
