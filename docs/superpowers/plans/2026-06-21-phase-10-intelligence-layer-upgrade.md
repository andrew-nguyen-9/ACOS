# Phase 10: Intelligence Layer Upgrade

**Date:** 2026-06-21
**Status:** Planning
**Phase Gate:** Phase 9 (Career Simulation & Strategy Engine) — 50/50 tests passing ✅

---

## Overview

Phase 10 upgrades ACOS from a retrieval-and-generation system into an evidence-reasoning system. The primary goal is to eliminate weak-confidence outputs by building a pipeline that explicitly reasons about evidence before generating content, self-corrects poor outputs, and maintains persistent memory of what has worked across sessions.

### Non-negotiable constraints (from CLAUDE.md)
- No external API calls — all models run via Ollama locally
- Every generated claim must cite an internal evidence record or be labeled `weak_inference`
- No hallucinated reasoning — LLM conclusions must reference provided evidence
- 90%+ test coverage on every new service

---

## Pre-Phase Fixes (Complete — delivered in this session)

These were blocking issues identified before Phase 10 planning:

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Incomplete bullets | LLM prompt limited to "≤25 words" — too short for quantified bullets | Updated `prompts/resume/generate.yaml` to "≤40 words, ≤175 chars" |
| DOCX missing header | `ResumeDOCXExporter` used `Document()` (blank) and ignored `template_name` | Rewrote to load matching `.docx` template, clear body, rebuild with proper header, Education, and section formatting |
| CL no letter format | `CoverLetterDOCXExporter` just dumped paragraphs | Added candidate header, date, Re: block, and closing per business letter spec |
| No template routing | `template_name` parameter was unused | Added `_TEMPLATE_FILES` map → 3 DOCX source files; section order varies by template |

---

## Phase 10 Architecture

```
JD Input
  ↓
[1] Query Understanding        ← new: extract intent, role type, seniority, must-haves
  ↓
[2] Multi-Vector Retrieval     ← upgrade: parallel ChromaDB + BM25 + recency-weighted SQL
  ↓
[3] Evidence Ranking           ← upgrade: MMR diversity + confidence × score weighting
  ↓
[4] Reasoning Layer            ← new: step-by-step match reasoning, contradiction detection
  ↓
[5] Context Memory             ← new: inject relevant past sessions and role-specific context
  ↓
[6] Self-Correction            ← new: score output, rewrite weak bullets, flag hallucinations
  ↓
DOCX / Cover Letter / Strategy output
```

---

## Module 1: Query Understanding Service

**Purpose:** Parse a job description into structured intent before retrieval — avoiding the "flood the retriever with full JD text" anti-pattern.

**Inputs:** Raw JD text (string)

**Outputs:**
```json
{
  "role_type": "product_management",
  "seniority": "senior",
  "required_skills": ["SQL", "Python", "roadmapping"],
  "preferred_skills": ["ML", "Tableau"],
  "must_have_keywords": ["cross-functional", "stakeholder"],
  "company_signals": ["B2B SaaS", "Series C"],
  "query_vectors": {
    "skills": "<embedding of skill list>",
    "responsibilities": "<embedding of responsibilities section>",
    "impact": "<embedding of impact requirements>"
  }
}
```

**Implementation:**
- `backend/services/intelligence/query_understander.py`
- Uses Ollama `qwen3:8b` to extract structured fields; falls back to regex/keyword rules if LLM unavailable
- Prompt: `backend/prompts/intelligence/understand_query.yaml`
- Produces 3 separate embeddings (skills, responsibilities, impact) for multi-vector retrieval

**Tests:** `backend/tests/unit/test_query_understander.py`
- Verify role_type classification across 5 role types
- Verify fallback when Ollama unavailable
- Verify keyword extraction is non-hallucinatory (only returns words present in JD)

---

## Module 2: Multi-Vector Retrieval Upgrade

**Purpose:** Replace the current single-vector ChromaDB query with parallel retrieval across 3 query vectors + recency-weighted SQL fallback.

**Current state:** `backend/services/evidence_selector.py` runs a single `collection.query()` with full JD text.

**Upgrade:**
```
query_vectors.skills → ChromaDB query → top-K skill-matched evidence
query_vectors.responsibilities → ChromaDB query → top-K responsibility-matched evidence
query_vectors.impact → ChromaDB query → top-K impact/metric evidence
SQL (recency-weighted) → recent roles × 1.2 boost, current role × 1.5 boost
```

Results merged via Maximal Marginal Relevance (MMR) to ensure diversity across roles and dimensions.

**Implementation:**
- `backend/services/intelligence/multi_vector_retriever.py`
- Wraps existing `EvidenceSelector` — no schema changes required
- MMR implemented as: iteratively select next candidate that maximizes (relevance × (1 - max_similarity_to_already_selected))

**Config:**
```python
MMR_LAMBDA = 0.5   # balance relevance vs. diversity
TOP_K_PER_VECTOR = 15
FINAL_POOL_SIZE = 30
```

**Tests:** `backend/tests/unit/test_multi_vector_retriever.py`

---

## Module 3: Evidence Ranking Upgrade

**Purpose:** Replace the 5-dimension `BulletScorer` with a combined relevance × confidence × recency score that also enforces dimension diversity.

**Current formula:** `score = weighted_sum(5 dimensions)`

**Upgraded formula:**
```
score = (0.4 × relevance) + (0.3 × confidence_weight) + (0.2 × dimension_coverage_bonus) + (0.1 × recency_weight)

confidence_weight: verified=1.0, strong_inference=0.7, weak_inference=0.3
dimension_coverage_bonus: +0.1 for each of 5 dimensions represented in top-10 set
recency_weight: current_role=1.0, ≤2yr=0.8, ≤5yr=0.6, >5yr=0.4
```

**Implementation:**
- Extend `backend/services/resume/bullet_scorer.py` — add `score_with_context()` method
- Pass `dimension_distribution` dict from prior selections to compute coverage bonus

---

## Module 4: Context Memory System

**Purpose:** Persist and retrieve session memory so later resume/CL generations build on what was learned from previous applications.

### Memory types

| Type | Storage | TTL | Description |
|------|---------|-----|-------------|
| Short-term | In-process dict | Session scope | Current session's JD, keywords, generated bullets |
| Long-term | SQLite `memory` table | Permanent | Which bullets performed well (got to interview), which were flagged |
| Role-specific | ChromaDB `acos_role_memory` | Permanent | Per-role-type patterns: what frameworks/verbs resonate |
| Company-specific | ChromaDB `acos_company_memory` | Permanent | Per-company: tone, emphasis, ATS keywords that passed screening |

### Schema additions

```sql
-- New migration: add_memory_table
CREATE TABLE memory (
    id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,           -- short_term, long_term, role_specific, company_specific
    role_type TEXT,                      -- product_management, consulting, etc.
    company TEXT,
    content_json TEXT NOT NULL,          -- serialized memory payload
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME                  -- NULL = permanent
);
CREATE INDEX idx_memory_role_type ON memory(role_type);
CREATE INDEX idx_memory_company ON memory(company);
```

**Implementation:**
- `backend/services/intelligence/context_memory.py`
- `backend/repositories/memory.py`
- `database/migrations/010_add_memory_table.py`

### Memory injection
At generation time, `ContextMemory.retrieve(role_type, company)` queries both SQLite and ChromaDB and prepends relevant memories to the evidence context passed to the LLM:
```
[MEMORY: At Accenture, bullets emphasizing cost savings performed best. ATS keywords: "cost optimization", "ROI"]
[MEMORY: product_management roles respond well to metrics-first bullet structure]
```

**Tests:** `backend/tests/unit/test_context_memory.py`, `backend/tests/integration/test_memory_routes.py`

---

## Module 5: Reasoning Layer

**Purpose:** Make the LLM show its work before generating output. Replaces single-shot generation with a two-step reason-then-write pattern.

### Step 1: Job Match Reasoning
Before generating resume content, the LLM produces a structured reasoning trace:
```json
{
  "role_alignment": {
    "strong_matches": ["SQL experience in evidence #3", "PM leadership in evidence #7"],
    "gaps": ["No ML experience found in evidence"],
    "confidence": 0.82
  },
  "evidence_synthesis": "The candidate's background in [X] maps to the JD's requirement for [Y]...",
  "contradiction_flags": ["Evidence #2 claims 'no ML experience' but #9 mentions 'built ML pipeline'"],
  "recommended_bullets": ["evidence_3", "evidence_7", "evidence_12"]
}
```

### Step 2: Grounded Generation
The reasoning trace + recommended evidence IDs are passed to the generation step. The LLM is instructed to generate bullets ONLY from the recommended set, citing the evidence ID for each.

**Implementation:**
- `backend/services/intelligence/reasoning_engine.py`
- `backend/prompts/intelligence/reason_job_match.yaml` (system + user template)
- `backend/prompts/intelligence/generate_grounded.yaml` (updated generate prompt with reasoning context)

**Tests:** `backend/tests/unit/test_reasoning_engine.py`
- Test contradiction detection
- Test that output bullets only reference recommended evidence IDs
- Test fallback to direct generation when Ollama unavailable

---

## Module 6: Model Orchestration

**Purpose:** Route generation requests to the right Ollama model configuration based on task type. Different tasks need different temperature/context-length settings.

| Mode | Task | Model | Temperature | Context |
|------|------|-------|------------|---------|
| `fast_retrieval` | Keyword extraction, embedding queries | `qwen3:8b` | 0.0 | 2048 |
| `deep_reasoning` | Job match reasoning, contradiction detection | `qwen3:8b` | 0.1 | 8192 |
| `ats_optimization` | ATS scoring, keyword density analysis | `qwen3:8b` | 0.0 | 4096 |
| `copilot` | Conversational career Q&A | `qwen3:8b` | 0.4 | 16384 |

**Implementation:**
- `backend/services/intelligence/model_orchestrator.py`
- Wraps the existing `OllamaClient` — no new dependencies
- Mode selected per call site; orchestrator selects temperature/context_window

**Tests:** `backend/tests/unit/test_model_orchestrator.py`

---

## Module 7: Embedding Intelligence Upgrade

**Purpose:** Improve ChromaDB retrieval precision by upgrading the chunking and indexing strategy.

### Current state
- Single-chunk indexing: full bullet text → embedding → ChromaDB
- All bullets in one collection (`acos_bullet_examples`)

### Upgrades

**7a. Semantic chunking**
Bullets chunked at sentence boundaries (not character count). Compound bullets ("Did X; achieved Y; resulting in Z") split into 3 separate embeddings, all with the same `source_evidence_id`.

**7b. Skill normalization**
Before embedding, skills are normalized via a lookup table:
```python
SKILL_ALIASES = {
    "ML": "machine learning",
    "NLP": "natural language processing",
    "A/B": "A/B testing",
    "PM": "product management",
}
```
This prevents "ML" and "machine learning" from occupying separate clusters in the embedding space.

**7c. Project-to-skill mapping**
Each project evidence record is expanded with inferred skills before embedding:
```
"Built a Tableau dashboard for supply chain metrics"
→ expanded: "Built a Tableau dashboard for supply chain metrics [skills: Tableau, data visualization, supply chain analytics]"
```

**7d. Separate collections by dimension**
Add 5 dimension-specific collections alongside the master collection:
- `acos_bullets_impact`
- `acos_bullets_leadership`
- `acos_bullets_technical`
- `acos_bullets_strategic`
- `acos_bullets_cross_functional`

Multi-vector retrieval queries dimension-specific collections when the JD strongly signals a particular dimension.

**Implementation:**
- `backend/services/intelligence/semantic_chunker.py`
- `backend/services/intelligence/skill_normalizer.py`
- `backend/services/intelligence/project_skill_mapper.py`
- Update `scripts/seed/load_bullet_seed.py` to use new chunking/normalization

---

## Module 8: Self-Correction System

**Purpose:** Score generated output before returning it, and automatically rewrite bullets below threshold.

### Correction triggers

| Condition | Action |
|-----------|--------|
| Bullet score < 3.0 / 5.0 on any dimension | Rewrite using `BulletRewriter.compress()` + LLM rephrase |
| Confidence = `weak_inference` without `⚠` marker | Add marker and set `requires_approval = True` |
| Skill mentioned in bullet not found in evidence | Flag as hallucination → remove skill claim |
| Duplicate experience (same achievement in 2 bullets) | Deduplicate, keep higher-scored version |
| Bullet > 175 chars | Compress via `BulletRewriter.compress()` until ≤ 175 |

**Implementation:**
- `backend/services/intelligence/self_corrector.py`
- Inserted into `ResumeGenerator.generate()` between Step 8 (validate) and Step 9 (ATS score)
- Max 2 correction iterations per bullet to prevent infinite loops

**Tests:** `backend/tests/unit/test_self_corrector.py`
- Test each correction trigger
- Test that correction never modifies `verified` bullets beyond compression
- Test max-iteration guard

---

## DOCX Template System (Delivered)

Dynamic template loading now routes `template_name` → actual `.docx` file in `mock-designs/resume-templates/`:

| Template name | Source file |
|--------------|-------------|
| `software`, `ai` | `Yale-College-General-Template-v.1.docx` |
| `product`, `data_analytics` | `Resume-Fewer-than-10-yrs.docx` |
| `consulting`, `healthcare` | `tMPA_Application_Resume_Template.docx` |

The exporter opens the template file (`Document(template_path)`) to inherit its fonts, margins, and styles, then clears body content and rebuilds with generated content. Section ordering varies by template (Yale puts Education first; others lead with Experience).

### Cover letter format
Now produces a full business letter: candidate header block (name + contact, centered, Arial 14pt), date, recipient block with Re: line, body paragraphs, and closing.

---

## Implementation Order

```
Phase 10.0: Pre-Phase Fixes (DONE)
  ✅ Prompt word limit: 25 → 40 words
  ✅ ResumeDOCXExporter: dynamic template + full header
  ✅ CoverLetterDOCXExporter: business letter format

Phase 10.1: Foundation (Week 1) — COMPLETE ✅
  ✅ Migration d1a2b3c4e5f6: memory table (8 cols, role/company indexes; up+down verified)
  ✅ Memory model + MemoryRepository (retrieve by role/company, expiry filter, prune) — 7 tests
  ✅ ContextMemory service (record/retrieve/format_for_injection/record_outcome) — 5 tests
  ✅ QueryUnderstander service + understand_query.yaml prompt — 6 tests
  ✅ All 629 tests pass, 91.33% coverage

Phase 10.2: Retrieval Upgrade (Week 1) — CORE COMPLETE ✅
  ✅ MultiVectorRetriever: 3 query vectors (skills/keywords/role) + dedup + MMR diversity — 6 tests
     (MMR uses word-overlap similarity; ceiling noted — upgrade to embedding cosine if needed)
  ✅ Evidence ranking upgrade: BulletScorer.score_with_context + dominant_dimension classifier — 6 tests
  ✅ 641 tests pass, 91.43% coverage

Phase 10.2b: Embedding Intelligence (Week 1) — COMPLETE ✅
  ✅ SkillNormalizer: alias canonicalization (ML→machine learning), whole-token — 5 tests
  ✅ SemanticChunker: split compound bullets on ;/sentence boundaries — 6 tests
  ✅ ProjectSkillMapper: append inferred [skills: ...] to project text — 4 tests
  ✅ IndexPreprocessor: composed normalize→expand→chunk entry point — 4 tests
  ⏳ DEFERRED: physical ChromaDB reseed (needs live Ollama embeddings) — wire
     IndexPreprocessor into load_bullet_seed.py + RAGIndexer on next reseed pass

Phase 10.3: Reasoning Layer (Week 2) — COMPLETE ✅
  ✅ ModelOrchestrator: mode→(temperature, max_tokens) routing; None when Ollama down — 5 tests
     (num_ctx not wired; ceiling noted — OllamaClient exposes no context window)
  ✅ ReasoningEngine: reason-then-write trace; recommended IDs filtered to evidence
     pool (AC-10-5 no hallucinated refs); deterministic fallback — 6 tests
  ✅ Prompt: reason_job_match.yaml
  ✅ Wired into ResumeGenerator (optional reasoning_engine; default None preserves
     behavior; filters bullets to recommendations) — 3 tests
  ✅ 674 tests pass, 91.61% coverage

Phase 10.3: Reasoning Layer (Week 2)
  [ ] ReasoningEngine service
  [ ] Prompts: reason_job_match.yaml, generate_grounded.yaml
  [ ] ModelOrchestrator (wraps OllamaClient)
  [ ] Wire reasoning into ResumeGenerator.generate()
  [ ] Tests: reasoning_engine, model_orchestrator

Phase 10.4: Self-Correction (Week 2)
  [ ] SelfCorrector service
  [ ] Wire into ResumeGenerator after validation step
  [ ] Tests: self_corrector

Phase 10.5: Integration + Acceptance
  [ ] End-to-end integration tests across all 8 modules
  [ ] Performance: full generate() ≤ 30s with Ollama running locally
  [ ] Update route handlers to accept/pass contact_info for DOCX export
```

---

## Acceptance Criteria

| ID | Criterion | How verified |
|----|-----------|-------------|
| AC-10-1 | Resume bullets never truncate mid-phrase | Prompt word limit = 40 words; validator enforces 175 chars |
| AC-10-2 | DOCX output matches visual style of source template | Smoke test: open exported file, verify Arial font, proper header |
| AC-10-3 | QueryUnderstander produces role_type and skill list from JD | Unit test with 5 fixture JDs |
| AC-10-4 | Multi-vector retrieval returns evidence from ≥3 different roles | Integration test |
| AC-10-5 | Reasoning trace cites only evidence IDs passed in context | Unit test asserts no invented IDs in output |
| AC-10-6 | Self-corrector catches bullets > 175 chars | Unit test with oversized bullet |
| AC-10-7 | Memory injection improves ATS score on second generation for same role | Integration test comparing score before/after memory |
| AC-10-8 | All new services have ≥90% test coverage | pytest-cov |
| AC-10-9 | No external API calls; Ollama-only | grep for requests.get / httpx in new service files |

---

## Files to Create

```
backend/
  services/
    intelligence/
      __init__.py
      query_understander.py
      multi_vector_retriever.py
      reasoning_engine.py
      model_orchestrator.py
      semantic_chunker.py
      skill_normalizer.py
      project_skill_mapper.py
      self_corrector.py
      context_memory.py
  repositories/
    memory.py
prompts/
  intelligence/
    understand_query.yaml
    reason_job_match.yaml
    generate_grounded.yaml
database/
  migrations/
    010_add_memory_table.py
backend/tests/
  unit/
    test_query_understander.py
    test_multi_vector_retriever.py
    test_reasoning_engine.py
    test_model_orchestrator.py
    test_self_corrector.py
    test_context_memory.py
  integration/
    test_intelligence_routes.py
    test_memory_routes.py
```

---

## Roadmap Impact

Phase 10 inserts between Phase 9 and the Frontend. Updated numbering:
- Phase 10: Intelligence Layer Upgrade ← this document
- Phase 11: Frontend (Tauri + React) ← was Phase 10
- Phase 12: Packaging & Release ← was Phase 11
