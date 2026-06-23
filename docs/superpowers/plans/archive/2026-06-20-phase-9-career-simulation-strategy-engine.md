---
title: "feat: Career Simulation & Strategy Engine"
date: 2026-06-20
sequence: "012"
type: feat
phase: "9"
depth: deep
---

# feat: Career Simulation & Strategy Engine (Phase 9)

## Summary

Builds a predictive career decision layer on top of all Phase 1–8 outputs. Six service classes under `backend/services/strategy/` compute role fit, career path probabilities, application priority, skill gaps, and resume strategy from internal data + Ollama. Adds an opt-in MBA resume corpus scraper and a 500-bullet ChromaDB training seed to improve generation quality. One new FastAPI router at `/api/v1/strategy`. All predictions are evidence-grounded with three-tier confidence; no hallucinated market data.

---

## Problem Frame

ACOS currently generates application materials reactively: user supplies a JD, system outputs resume + cover letter + ATS score. Phase 9 makes ACOS proactive: given the user's history and target role categories, it answers *which jobs to pursue*, *which skills block progress*, *what conversion rates to expect*, and *which resume strategy maximizes success* — before a single application is submitted.

**Actors:**
- User (Andrew) — requests strategy recommendations and approves any applied changes
- ACOS Backend — computes recommendations from internal data only
- Ollama (Qwen3 8B) — LLM-assisted gap analysis when local data is thin
- MBA Corpus Scraper — opt-in enrichment from public university resume books

**Key constraint:** Zero hallucination. All probabilities must derive from actual `OutcomeSignal` rows or be flagged `weak_inference` when n < 3.

---

## Requirements

| ID | Requirement |
|----|-------------|
| R1 | RoleFitScorer computes 0–100 fit score for any JD with 4 sub-scores and confidence tier |
| R2 | CareerPathSimulator outputs interview + offer probability per career category |
| R3 | ApplicationStrategyEngine ranks jobs as prioritize / tailor / skip / bridge |
| R4 | SkillGapForecaster ranks missing skills by expected interview lift per hour invested |
| R5 | ResumeStrategySelector returns recommendation only; never applies without explicit user approval |
| R6 | HistoricalOutcomeLearner extends Phase 8 outcome ranker with category-level and timeline analytics |
| R7 | MBA Corpus Scraper fetches public resume books; parses bullets; seeds ChromaDB `acos_bullet_examples` collection |
| R8 | 500-bullet seed file loads into `acos_bullet_examples` collection with role_type and dimension metadata |
| R9 | `GET /api/v1/analytics/outcomes` returns extended outcome report (roadmap Phase 9 deliverable) |
| R10 | All predictions carry confidence: `verified` (n≥10), `strong_inference` (n 3–9), `weak_inference` (n<3) |
| R11 | Unit test coverage ≥90% on all new services; integration tests for all routes |

---

## Key Technical Decisions

**KTD-1: Career category taxonomy — hardcoded 6 + position_type mapping**
Six categories (Product Management, Data Analytics, Litigation Consulting, AI/ML, Consulting, TPM/Solutions Engineering) are hardcoded with keyword signature sets. `application.position_type` maps to these via a lookup dict. Dynamic derivation requires sufficient labeled history; hardcoding gives stable simulation targets the user can reason about.

**KTD-2: Sparse data — confidence tiers, no fabricated benchmarks**
When n < 3 for a category, CareerPathSimulator uses ATS score distribution + BulletScorer averages as proxy signals, clearly labeled `weak_inference`. It never invents market conversion rates. Better to show a weak-inference signal than false precision.

**KTD-3: Two-step approval gate for ResumeStrategySelector**
`GET /strategy/resume-recommendation` returns `ResumeStrategyRecommendation(requires_approval=True)`. A separate `POST /strategy/resume-recommendation/apply` writes to `system_config` as pending and emits a confirmation event. Spec-mandated; prevents accidental resume template changes.

**KTD-4: MBA scraper as opt-in enrichment only**
Scraper triggers via `POST /strategy/enrich-corpus`. Uses existing PDF parser + entity extractor. Respects robots.txt and rate limits 1 req/5s per domain. Results stored in `acos_bullet_examples`. External data never flows in during normal ACOS operation.

**KTD-5: 500-bullet seed as ChromaDB few-shot examples**
Bullets embed into `acos_bullet_examples` and are retrieved by BulletRewriter as top-k few-shot context per role_type + dimension. Improves generation quality without model fine-tuning or changes to the Ollama layer.

---

## High-Level Technical Design

```mermaid
flowchart TD
    subgraph Inputs
        JD[Job Description Text]
        DB[(SQLite: OutcomeSignal\nSkill, Experience, Application)]
        CDB[(ChromaDB: acos_bullet_examples)]
    end

    subgraph Strategy Services
        KE[KeywordExtractor]
        ATS[ATSScorer]
        RFS[RoleFitScorer]
        SIM[CareerPathSimulator]
        ASE[ApplicationStrategyEngine]
        SGF[SkillGapForecaster]
        RSS[ResumeStrategySelector]
        OL[OutcomeLearner]
    end

    subgraph Enrichment
        SCRAPER[MBACorpusScraper]
        SEED[BulletSeedLoader]
    end

    subgraph Output
        ROUTE[/api/v1/strategy]
    end

    JD --> KE --> RFS
    JD --> ATS --> RFS
    DB --> RFS
    DB --> SIM
    DB --> SGF
    DB --> RSS
    DB --> OL
    RFS --> ASE
    SIM --> ROUTE
    ASE --> ROUTE
    SGF --> ROUTE
    RSS --> ROUTE
    OL --> ROUTE
    SCRAPER --> CDB
    SEED --> CDB
    CDB --> RSS
```

**RoleFitScorer data flow:**
1. `POST /strategy/role-fit` receives JD text
2. `KeywordExtractor` → `required_skills[]`, `keywords[]`
3. `ATSScorer` → `experience_score`, `industry_score`
4. `SkillRepository` → user's verified skills
5. `OutcomeSignalRepository` → avg `signal_weight` for same industry
6. `RoleFitScorer` aggregates → `RoleFitScore` with confidence tier

**Confidence ladder:**

| n outcomes in category | confidence |
|------------------------|-----------|
| ≥ 10 | `verified` |
| 3 – 9 | `strong_inference` |
| < 3 | `weak_inference` (ATS-proxy signals only) |

---

## Output Structure

```
backend/
  models/
    strategy.py                              ← new: Pydantic strategy models
  services/
    strategy/
      __init__.py                            ← new
      role_fit_scorer.py                     ← new
      career_path_simulator.py               ← new
      application_strategy.py               ← new
      skill_gap_forecaster.py               ← new
      resume_strategy_selector.py           ← new
      outcome_learner.py                    ← new (wraps learning/ranker.py)
      corpus_scraper.py                     ← new: MBA resume web scraper
  api/v1/routes/
    strategy.py                             ← new
  main.py                                   ← modify: register strategy router
  tests/
    unit/
      test_role_fit_scorer.py               ← new
      test_career_path_simulator.py         ← new
      test_application_strategy.py         ← new
      test_skill_gap_forecaster.py         ← new
      test_resume_strategy_selector.py     ← new
      test_outcome_learner.py              ← new
      test_corpus_scraper.py               ← new
      test_bullet_seed_format.py           ← new
    integration/
      test_strategy_routes.py              ← new
  prompts/
    strategy/
      role_fit.yaml                        ← new
      skill_gap.yaml                       ← new
scripts/seed/
  bullet_training_data.py                  ← new: 500 bullet examples
  load_bullet_seed.py                      ← new: embeds + loads into ChromaDB
database/migrations/
  0020_create_strategy_tables.sql          ← new: role_fit_cache, skill_gaps
```

---

## Implementation Units

### U1. Strategy Pydantic Models

**Goal:** Define all request/response types for the strategy engine.

**Requirements:** R1, R2, R3, R4, R5, R10

**Dependencies:** None

**Files:**
- `backend/models/strategy.py` (create)

**Approach:**
- `ConfidenceTier`: `Literal["verified", "strong_inference", "weak_inference"]`
- `CareerCategory`: `Enum` with 6 values: product_management, data_analytics, litigation_consulting, ai_ml, consulting, tpm_solutions
- `RoleFitScore`: `overall: float`, `skill_overlap: float`, `experience_alignment: float`, `industry_alignment: float`, `historical_similarity: float`, `explanation: str`, `risk_factors: list[str]`, `missing_critical_skills: list[str]`, `confidence: ConfidenceTier`
- `CareerPathResult`: `category: CareerCategory`, `interview_probability: float | None`, `offer_probability: float | None`, `expected_timeline_days: int | None`, `difficulty_rating: float | None`, `sample_size: int`, `confidence: ConfidenceTier`
- `JobPriorityAction`: `Literal["prioritize", "tailor", "skip", "bridge"]`
- `ApplicationPriority`: `job_id: str | None`, `jd_text: str`, `priority: JobPriorityAction`, `reason: str`, `fit_score: float`
- `SkillGapItem`: `skill_name: str`, `gap_type: Literal["missing", "weak"]`, `frequency: int`, `blocking_interviews: bool`, `expected_lift_per_hour: float | None`, `priority_rank: float`
- `ResumeStrategyRecommendation`: `template_name: str`, `bullet_emphasis: list[str]`, `keyword_priorities: list[str]`, `reason: str`, `requires_approval: Literal[True] = True`
- `OutcomeReport`: extends existing ranker output; adds `category_breakdown: list[CareerPathResult]`, `timeline_analytics: dict[str, float | None]`, `ats_threshold: float | None`

**Test scenarios:**
- All Pydantic models validate correct inputs without error
- `ConfidenceTier` rejects invalid string values
- `requires_approval` field: `Literal[True]` means it cannot be set to `False`
- `CareerCategory` enum: all 6 values present, no extras
- `RoleFitScore.overall` rejects values outside 0–100

---

### U2. RoleFitScorer

**Goal:** Compute a 0–100 role fit score for any JD against user profile.

**Requirements:** R1, R10

**Dependencies:** U1

**Files:**
- `backend/services/strategy/role_fit_scorer.py` (create)
- `backend/tests/unit/test_role_fit_scorer.py` (create)
- `backend/prompts/strategy/role_fit.yaml` (create)

**Approach:**
Four sub-scores, each 0.0–1.0, weighted into overall score:

| Sub-score | Weight | Source |
|-----------|--------|--------|
| `skill_overlap` | 0.30 | `required_skills` from KeywordExtractor ∩ user Skill table / total required |
| `experience_alignment` | 0.30 | ATSScorer `experience_score` / 100 |
| `industry_alignment` | 0.20 | avg `signal_weight` for OutcomeSignals in same industry; fallback to 0.5 |
| `historical_similarity` | 0.20 | keyword Jaccard similarity to past JDs, weighted by their `signal_weight` |

`overall = round((0.30*skill_overlap + 0.30*experience_alignment + 0.20*industry_alignment + 0.20*historical_similarity) * 100, 1)`

`missing_critical_skills`: required_skills not in user skill table with proficiency ≥ intermediate.

`risk_factors`: generated from missing_critical_skills + industry mismatch.

`confidence`: based on n of OutcomeSignals in same industry (R10 tiers).

Uses `role_fit.yaml` prompt only when Ollama is available and n < 3 (weak_inference fallback to get explanation text).

**Patterns to follow:** `backend/services/ats/scorer.py` — sync method, Ollama optional, fallback path when unavailable.

**Test scenarios:**
- JD with all required_skills in user's skill table → `skill_overlap = 1.0`
- JD with 0 matching required_skills → `missing_critical_skills` populated, `skill_overlap = 0.0`
- No historical OutcomeSignals for industry → `historical_similarity = 0.5`, `confidence = "weak_inference"`
- n ≥ 10 OutcomeSignals in same industry → `confidence = "verified"`
- `overall` is weighted sum of sub-scores × 100, not clamped above 100
- Missing critical skill appears in both `risk_factors` and `missing_critical_skills`
- Ollama unavailable → falls back to keyword-based `explanation`, no crash

---

### U3. CareerPathSimulator

**Goal:** Simulate interview/offer probabilities across 6 career categories from application history.

**Requirements:** R2, R10

**Dependencies:** U1

**Files:**
- `backend/services/strategy/career_path_simulator.py` (create)
- `backend/tests/unit/test_career_path_simulator.py` (create)

**Approach:**
Hardcoded category taxonomy (keyword signatures for JD text matching):

```python
CATEGORY_KEYWORDS = {
    CareerCategory.product_management: ["product", "roadmap", "stakeholder", "user research", "OKR", "PRD", "sprint", "product manager"],
    CareerCategory.data_analytics: ["analytics", "SQL", "python", "dashboard", "ETL", "tableau", "pipeline", "data analyst"],
    CareerCategory.litigation_consulting: ["litigation", "legal", "expert", "damages", "discovery", "eDiscovery", "forensic"],
    CareerCategory.ai_ml: ["machine learning", "LLM", "NLP", "model", "AI", "deep learning", "MLOps", "data scientist"],
    CareerCategory.consulting: ["strategy", "client", "workstream", "engagement", "advisory", "management consulting"],
    CareerCategory.tpm_solutions: ["TPM", "solutions engineer", "implementation", "integration", "customer success", "technical program"],
}
POSITION_TYPE_MAP = {
    "pm": CareerCategory.product_management,
    "data": CareerCategory.data_analytics,
    "legal": CareerCategory.litigation_consulting,
    "ml": CareerCategory.ai_ml,
    "consulting": CareerCategory.consulting,
    "tpm": CareerCategory.tpm_solutions,
    "se": CareerCategory.tpm_solutions,
}
```

For each category: join `OutcomeSignal` → `Application` where `position_type` maps to category OR JD text contains category keywords.

Compute:
- `interview_probability` = count(signal_weight > 0.3) / total
- `offer_probability` = count(signal_weight ≥ 0.85) / total
- `expected_timeline_days` = avg days from `date_applied` → first interview `ApplicationTimeline` event
- `difficulty_rating` = 1.0 − interview_probability

When n < 3: set probabilities to `None`, `difficulty_rating` to `None`, flag `weak_inference`.

**Patterns to follow:** `backend/services/learning/ranker.py` OutcomeSignal aggregation pattern.

**Test scenarios:**
- 0 outcomes in category → `confidence = "weak_inference"`, probabilities = `None`
- 5 outcomes, 2 reached interview → `interview_probability = 0.40`, `confidence = "strong_inference"`
- 10 outcomes, 1 offer → `offer_probability = 0.10`, `confidence = "verified"`
- `position_type = "pm"` maps to `product_management` category
- All 6 CareerCategories present in output even when some have no data
- `difficulty_rating = 1.0 - interview_probability` (not clamped)

---

### U4. ApplicationStrategyEngine

**Goal:** Given a list of JDs, classify each as prioritize / tailor / bridge / skip.

**Requirements:** R3

**Dependencies:** U1, U2

**Files:**
- `backend/services/strategy/application_strategy.py` (create)
- `backend/tests/unit/test_application_strategy.py` (create)

**Approach:**
For each JD in input list:
1. Run `RoleFitScorer` → `fit_score`, `missing_critical_skills`
2. Apply priority rules:
   - `fit_score ≥ 75` AND `len(missing_critical_skills) ≤ 1` → **"prioritize"**
   - `fit_score 55–74` → **"tailor"**
   - `fit_score 40–54` OR (`fit_score < 55` AND gaps are bridgeable) → **"bridge"**
   - `fit_score < 40` OR `len(missing_critical_skills) > 3` → **"skip"**
3. Reason string cites `fit_score` + missing skills (no LLM call; purely computed)

Bridgeable gap: skill exists in user's skill table at `exposure` or `beginner` proficiency (i.e., already learning it).

Return `list[ApplicationPriority]` sorted by `fit_score` descending.

**Test scenarios:**
- `fit_score=80`, 0 missing → `priority = "prioritize"`
- `fit_score=60` → `priority = "tailor"`
- `fit_score=35` → `priority = "skip"`
- `fit_score=45`, 1 bridgeable gap → `priority = "bridge"`
- `fit_score=80`, 4 missing critical → `priority = "skip"` (critical skill gate overrides score)
- Empty input → empty output, no error
- `reason` string contains `fit_score` value and at least one missing skill if any

---

### U5. SkillGapForecaster

**Goal:** Rank missing skills by expected interview lift per hour invested.

**Requirements:** R4, R10

**Dependencies:** U1

**Files:**
- `backend/services/strategy/skill_gap_forecaster.py` (create)
- `backend/tests/unit/test_skill_gap_forecaster.py` (create)
- `backend/prompts/strategy/skill_gap.yaml` (create)

**Approach:**
1. Aggregate `missing_keywords` from recent ATSScorer results (last 90 days of applications)
2. Cross-reference with user's Skill table (flag as `missing` if absent, `weak` if proficiency < intermediate)
3. For each gap skill:
   - `frequency`: count of applications where skill was in `missing_keywords`
   - `blocking_interviews`: True if avg `signal_weight` for applications WITH the skill > WITHOUT it (from OutcomeSignal history)
   - `hours_to_acquire`: hardcoded lookup table (falls back to 40h for unknown skills)
   - `expected_lift_per_hour = (rate_with − rate_without) / hours_to_acquire` (None when n < 3)
   - `priority_rank = frequency × (expected_lift_per_hour or 0.01)`

Hours lookup table (approximate, directional only):

```python
HOURS_TO_ACQUIRE = {
    "python": 40, "SQL": 20, "tableau": 10, "power bi": 8,
    "scikit-learn": 20, "fastapi": 15, "docker": 10, "kubernetes": 30,
    "dbt": 12, "airflow": 15, "spark": 25, "tensorflow": 40,
    "react": 30, "typescript": 20, "terraform": 20, "aws": 40,
    "looker": 8, "snowflake": 10, "bigquery": 8, "databricks": 15,
}
```

**Test scenarios:**
- Skill in 5/5 missing_keywords lists → `frequency = 5`
- User has "python" at expert → not flagged (not missing, not weak)
- User has "sql" at beginner → flagged as `weak`
- Unknown skill defaults to `hours_to_acquire = 40`
- `priority_rank` ordering: high-frequency + high-lift ranked first
- `expected_lift_per_hour = None` when n < 3 (not fabricated)
- Empty application history → empty list, no error

---

### U6. ResumeStrategySelector

**Goal:** Recommend best template + bullet emphasis per role category; never auto-apply.

**Requirements:** R5

**Dependencies:** U1

**Files:**
- `backend/services/strategy/resume_strategy_selector.py` (create)
- `backend/tests/unit/test_resume_strategy_selector.py` (create)

**Approach:**
1. Call `Evaluator.template_effectiveness()` → ranked templates with interview rates
2. Map `role_category → bullet_emphasis` using hardcoded per-category dimension priorities:
   - `product_management`: `["leadership", "impact", "strategic"]`
   - `data_analytics`: `["technical", "quantification", "impact"]`
   - `ai_ml`: `["technical", "impact", "quantification"]`
   - `consulting`: `["strategic", "impact", "leadership"]`
   - `litigation_consulting`: `["technical", "impact", "strategic"]`
   - `tpm_solutions`: `["leadership", "cross_functional", "impact"]`
3. Select top template for category based on interview rate; fallback to "standard" if no data
4. `keyword_priorities`: top 5 keywords from category taxonomy
5. Always return `requires_approval=True` — never a flag, never overridable

Apply endpoint (`POST /strategy/resume-recommendation/apply`) writes recommendation to `system_config` table as `{"type": "strategy_recommendation", "status": "pending_user_confirmation", ...}`. Does not modify any Resume record.

**Test scenarios:**
- `requires_approval` is always `True`, cannot be set to `False`
- `template_effectiveness()` empty → returns `template_name = "standard"`, no error
- `role_category = product_management` → `bullet_emphasis` includes `"leadership"`
- `role_category = data_analytics` → `bullet_emphasis` includes `"quantification"`
- Apply endpoint: writes to `system_config`, not to `resumes` table
- Apply endpoint: returns `{"status": "pending_user_confirmation"}`, not `"applied"`

---

### U7. HistoricalOutcomeLearner

**Goal:** Extend Phase 8 outcome ranker with category-level analytics and timeline metrics.

**Requirements:** R6, R9

**Dependencies:** U1, U3

**Files:**
- `backend/services/strategy/outcome_learner.py` (create)
- `backend/tests/unit/test_outcome_learner.py` (create)

**Approach:**
Wraps existing `OutcomeRanker` and `Evaluator` without modifying them. Adds:

- `category_breakdown()`: runs CareerPathSimulator, returns `list[CareerPathResult]` — per-category stats mapped to the 6 fixed categories
- `timeline_analytics()`: queries `ApplicationTimeline` for avg days between status transitions: `draft→applied`, `applied→phone_screen`, `phone_screen→interview`, `interview→final_round`, `final_round→offer`. Returns `None` for stages with no data.
- `ats_threshold_analysis()`: find the minimum ATS score bucket (0-20, 20-40, etc.) where interview rate exceeds 50%. Returns `None` if no bucket crosses threshold.
- `get_extended_report() → OutcomeReport`: combines `OutcomeRanker` output + `Evaluator` output + `category_breakdown` + `timeline_analytics` + `ats_threshold`

`GET /analytics/outcomes` calls `get_extended_report()` and fulfills the roadmap Phase 9 deliverable.

**Test scenarios:**
- `category_breakdown()` returns all 6 categories (including empty ones)
- `timeline_analytics()` returns `None` for any stage with no ApplicationTimeline data
- `ats_threshold_analysis()`: if interview_rate > 50% starts at bucket 60-80, returns `60.0`
- `OutcomeReport` serializes to JSON cleanly (all fields JSON-serializable)
- Wraps OutcomeRanker without modifying its source file

---

### U8. MBA Resume Corpus Scraper

**Goal:** Fetch public MBA resume books; extract bullet points; seed `acos_bullet_examples` ChromaDB collection.

**Requirements:** R7

**Dependencies:** Existing `PDFParser` (`backend/ingestion/parsers/pdf.py`), `Embedder`, `ChromaDB` client

**Files:**
- `backend/services/strategy/corpus_scraper.py` (create)
- `backend/tests/unit/test_corpus_scraper.py` (create)

**Approach:**
Known public sources (PDFs published by university career services — URL allowlist hardcoded):

```python
CORPUS_SOURCES = [
    {"name": "Wharton MBA Resume Guide", "url": "...", "type": "guide"},
    {"name": "MIT Sloan Career Resources", "url": "...", "type": "guide"},
    {"name": "Kellogg Resume Examples", "url": "...", "type": "examples"},
    {"name": "Booth Career Services", "url": "...", "type": "guide"},
]
```

Scraper pipeline:
1. Check URL against hardcoded allowlist (reject if not present)
2. Check `robots.txt` via `urllib.robotparser`; skip if disallowed
3. Fetch with `requests` (timeout=30s, `User-Agent: ACOS/1.0 career-research-bot`)
4. Rate limit: `time.sleep(5)` between requests to same domain
5. Pass bytes to existing `PDFParser` → raw text
6. Extract bullets via regex: lines 40–200 chars, start with uppercase word, contain an action verb from Phase 8.1 verb list
7. Deduplicate via SHA-256 of `text.strip().lower()`
8. Embed via `Embedder` + store in `acos_bullet_examples` with metadata: `source`, `role_type_hint` (inferred from section header keywords), `has_metric` (bool: contains digit or %)
9. Catch all exceptions per-URL; log failure; continue (never crash)
10. Return `{"bullets_added": int, "urls_processed": int, "urls_failed": int}`

Security: URL allowlist enforced before any fetch; never exec parsed content; path traversal impossible (no file writes from scraped content); all malformed PDF errors caught.

**Patterns to follow:** `backend/ingestion/security.py` for validation patterns; `backend/ingestion/parsers/pdf.py` for PDF parsing.

**Test scenarios:**
- URL not in allowlist → raises `ValueError`, no HTTP request made
- `robots.txt` disallows scraping → URL skipped, counted in `urls_failed`
- Malformed PDF bytes → caught, logged, counted in `urls_failed`, no crash
- Bullet regex: matches "Led cross-functional team of 8 to deliver..." ✓
- Bullet regex: rejects "See above for context" (too generic) ✗
- Bullet regex: rejects single-word lines ✗
- Duplicate bullet (same SHA-256) → skipped, not re-added to collection
- Return dict has all three keys: `bullets_added`, `urls_processed`, `urls_failed`

---

### U9. Bullet Training Data Seed

**Goal:** Load 500 hand-curated bullet examples into ChromaDB for BulletRewriter few-shot context.

**Requirements:** R8

**Dependencies:** `Embedder`, ChromaDB client

**Files:**
- `scripts/seed/bullet_training_data.py` (create — contains 500 bullets as Python list)
- `scripts/seed/load_bullet_seed.py` (create — embeds + loads into ChromaDB)
- `backend/tests/unit/test_bullet_seed_format.py` (create)

**Approach:**
500 bullets organized by `role_type × dimension`:

| `role_type` | count |
|-------------|-------|
| `product_management` | 100 |
| `data_analytics` | 100 |
| `consulting` | 100 |
| `engineering` | 100 |
| `tpm_solutions` | 100 |

Each bullet: `{"text": str, "role_type": str, "dimension": str, "verb": str, "has_metric": bool}`

Dimensions: `impact`, `leadership`, `technical`, `strategic`, `cross_functional`

`load_bullet_seed.py`:
1. Import `BULLET_EXAMPLES` from `bullet_training_data.py`
2. For each bullet: compute SHA-256 of text; skip if already in `acos_bullet_examples`
3. Embed text → store with all dict fields as ChromaDB metadata
4. Print progress every 50 bullets; print summary at end
5. Idempotent: safe to run multiple times

BulletRewriter integration: query `acos_bullet_examples` for top-3 results matching `role_type` + `dimension` before generating; inject as few-shot examples in the Ollama prompt.

**Test scenarios:**
- `bullet_training_data.py` contains exactly 500 entries in `BULLET_EXAMPLES`
- Each entry has all required keys: `text`, `role_type`, `dimension`, `verb`, `has_metric`
- No bullet `text` exceeds 250 characters
- All 5 role_types present with ≥ 90 bullets each
- All 5 dimensions present across the set
- `has_metric` is `bool`, not string
- `load_bullet_seed.py` running twice → same final collection count (idempotent)

---

### U10. Strategy API Routes

**Goal:** Wire all strategy services to FastAPI routes under `/api/v1/strategy`.

**Requirements:** R1–R9

**Dependencies:** U2–U9

**Files:**
- `backend/api/v1/routes/strategy.py` (create)
- `backend/tests/integration/test_strategy_routes.py` (create)
- `backend/main.py` (modify: register strategy router with prefix `/api/v1`)

**Approach:**

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/strategy/role-fit` | `{jd_text: str, resume_id?: str}` | `RoleFitScore` |
| GET | `/strategy/career-paths` | — | `list[CareerPathResult]` |
| POST | `/strategy/prioritize` | `{jobs: list[{jd_text, job_id?}]}` | `list[ApplicationPriority]` |
| GET | `/strategy/skill-gaps` | — | `list[SkillGapItem]` |
| GET | `/strategy/resume-recommendation` | `?role_category=` | `ResumeStrategyRecommendation` |
| POST | `/strategy/resume-recommendation/apply` | `{recommendation_id: str}` | `{status: str}` |
| POST | `/strategy/enrich-corpus` | — | `{bullets_added, urls_processed, urls_failed}` |
| GET | `/analytics/outcomes` | — | `OutcomeReport` |

All routes return standard error envelope (existing `backend/api/errors.py`). Services injected via FastAPI `Depends`.

**Patterns to follow:** `backend/api/v1/routes/resume.py` and `backend/api/v1/routes/learning.py`.

**Test scenarios:**
- `POST /strategy/role-fit` with valid JD → 200, `RoleFitScore` shape validated
- `POST /strategy/role-fit` with empty `jd_text` → 422
- `GET /strategy/career-paths` → 200, all 6 categories in response
- `POST /strategy/prioritize` with empty `jobs` list → 200, empty list
- `GET /strategy/skill-gaps` with no application history → 200, empty list
- `GET /strategy/resume-recommendation` missing `role_category` param → 422
- `POST /strategy/resume-recommendation/apply` → `status = "pending_user_confirmation"` (not `"applied"`)
- `POST /strategy/enrich-corpus` → 200, response has `bullets_added` int
- `GET /analytics/outcomes` → 200, `OutcomeReport` with `category_breakdown` list

---

### U11. Database Migration

**Goal:** Add tables for role fit result caching and persisted skill gap analysis.

**Requirements:** R1, R4

**Dependencies:** None

**Files:**
- `database/migrations/0020_create_strategy_tables.sql` (create)

**Approach:**

```sql
-- role_fit_cache: avoid re-scoring same JD text
CREATE TABLE IF NOT EXISTS role_fit_cache (
    id                    TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    jd_hash               TEXT NOT NULL UNIQUE,
    fit_score             REAL NOT NULL,
    skill_overlap         REAL NOT NULL,
    experience_alignment  REAL NOT NULL,
    industry_alignment    REAL NOT NULL,
    historical_similarity REAL NOT NULL,
    explanation           TEXT,
    missing_critical_skills TEXT NOT NULL DEFAULT '[]',
    confidence            TEXT NOT NULL CHECK (confidence IN ('verified','strong_inference','weak_inference')),
    computed_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- skill_gaps: persisted gap analysis for dashboard
CREATE TABLE IF NOT EXISTS skill_gaps (
    id                     TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    skill_name             TEXT NOT NULL,
    gap_type               TEXT NOT NULL CHECK (gap_type IN ('missing','weak')),
    frequency              INTEGER NOT NULL DEFAULT 0,
    blocking_interviews    INTEGER NOT NULL DEFAULT 0,
    expected_lift_per_hour REAL,
    priority_rank          REAL NOT NULL DEFAULT 0.0,
    computed_at            TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Test scenarios:**
- Migration runs cleanly on fresh SQLite file
- `role_fit_cache` unique constraint on `jd_hash` (insert duplicate → error)
- `skill_gaps.gap_type` check rejects values outside `('missing','weak')`
- `role_fit_cache.confidence` check rejects invalid confidence values

---

## Scope Boundaries

**In scope (Phase 9):**
- Six strategy services + API router
- MBA corpus scraper (opt-in via explicit API call)
- 500-bullet seed data + ChromaDB loader
- `GET /analytics/outcomes` (roadmap Phase 9 deliverable)
- Database migration for caching tables

**Deferred to Follow-Up Work:**
- Frontend strategy dashboard UI (Phase 10)
- Automated corpus refresh schedule (post-Phase 11)
- LinkedIn / Indeed JD batch import for bulk prioritization
- Slack/email alert when high-fit JD is detected

**Outside this product's identity:**
- External market salary benchmarking via third-party APIs
- Real-time job board scraping for live JD feeds
- Automated application submission

---

## Risks & Dependencies

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Few OutcomeSignals → most predictions `weak_inference` | Medium | Confidence tiers surface this; simulator still gives directional signal; improves automatically with more applications |
| MBA resume PDFs change URL or block scraping | Low | Hardcoded allowlist; graceful skip on 403/404; 500-bullet local seed is standalone fallback |
| BulletRewriter few-shot context too long for Ollama | Low | Retrieve top-3 examples per dimension only; not all 500 |
| Career category mapping incorrect for edge-case JD | Medium | Keyword signature fallback + explicit `confidence = "weak_inference"` flag |
| `hours_to_acquire` lookup is imprecise | Low | Directional only; labeled as such in `SkillGapItem`; users can override via UI in Phase 10 |

---

## Sources & Research

- `backend/services/ats/scorer.py` — ATSScorer sub-score and fallback pattern
- `backend/services/learning/ranker.py` — OutcomeSignal aggregation pattern
- `backend/services/optimization/evaluator.py` — `template_effectiveness()` and `industry_effectiveness()`
- `backend/services/optimization/recommender.py` — confidence level + rationale model
- `backend/services/resume/bullet_scorer.py` — 5-dimension scoring weights and patterns
- `backend/models/application.py` — Application + ApplicationTimeline fields
- `backend/models/outcome.py` — OutcomeSignal fields (signal_weight, industry, position_type)
- `docs/08_ROADMAP.md` Phase 9 — `GET /analytics/outcomes` requirement
- `docs/04_DATABASE_SCHEMA.md` — OutcomeSignal, Application, Skill, Experience table contracts
