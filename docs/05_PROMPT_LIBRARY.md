# ACOS Prompt Library

## Design Principles

- Every prompt is a versioned, self-documenting YAML file
- Prompts never contain user-specific data — only templates
- All variable substitution uses `{{variable_name}}` syntax
- Input and output schemas are explicit — callers validate before sending
- Prompts include a `confidence_rules` block defining what level of evidence is needed for each claim
- No prompt may instruct the model to invent metrics, dates, employers, certifications, or projects

---

## File Format

```yaml
# backend/prompts/<module>/<name>.yaml

name: resume_generate
version: "1.0.0"
module: resume
purpose: >
  Generate a tailored, ATS-optimized one-page resume from structured career data
  and a job description. All bullets must be grounded in provided evidence.

model: "{{system.default_model}}"   # resolved from system_config at runtime
temperature: 0.3                    # low for factual generation
max_tokens: 4096

input_schema:
  job_description: string
  company: string
  position: string
  industry: string
  experiences: list[ExperienceBulletSet]
  projects: list[ProjectSummary]
  skills: list[SkillRecord]
  template_layout: string

output_schema:
  resume_json:
    header: ContactBlock
    summary: string | null
    experience: list[ExperienceBlock]
    projects: list[ProjectBlock]
    skills: SkillsBlock
    education: EducationBlock
  confidence_map: dict[str, ConfidenceLevel]

confidence_rules:
  verified: "Direct evidence from provided records"
  strong_inference: "Multiple supporting records; no invention"
  weak_inference: "Model-generated; requires user review before use"
  prohibited: "Metrics, dates, employers, certs not in provided data"

system_prompt: |
  You are a resume generation engine. Your only job is to transform provided
  career evidence into a one-page, ATS-optimized resume.

  HARD RULES:
  - You may only use information present in the provided records.
  - Never invent metrics, percentages, dates, company names, certifications, or project names.
  - If evidence is weak or inferred, mark it with confidence: weak_inference.
  - Output ONLY valid JSON matching output_schema.
  - The resume must fit exactly one page when rendered at standard font sizes.

user_prompt: |
  Job: {{position}} at {{company}}
  Industry: {{industry}}

  Job Description:
  {{job_description}}

  Career Evidence:
  {{experiences_json}}
  {{projects_json}}
  {{skills_json}}

  Generate the resume JSON. For every bullet, include its confidence level.
```

---

## Prompt Catalog

### Module: `resume/`

| File | Purpose |
|------|---------|
| `resume/generate.yaml` | Generate full resume JSON from career evidence + JD |
| `resume/score_ats.yaml` | Score a resume against a job description |
| `resume/extract_keywords.yaml` | Extract must-have keywords from a JD |
| `resume/select_bullets.yaml` | Rank and select best bullets for a given role |
| `resume/rewrite_bullet.yaml` | Strengthen a weak bullet using evidence |

---

### Module: `cover_letter/`

| File | Purpose |
|------|---------|
| `cover_letter/generate.yaml` | Generate cover letter from evidence + JD |
| `cover_letter/learn_voice.yaml` | Extract writing profile from historical cover letters |
| `cover_letter/apply_voice.yaml` | Rewrite draft using learned voice profile |

---

### Module: `ats/`

| File | Purpose |
|------|---------|
| `ats/analyze.yaml` | Full ATS analysis: keyword match, skill gap, score |
| `ats/extract_requirements.yaml` | Extract required vs. preferred qualifications from JD |
| `ats/suggest_additions.yaml` | Recommend missing keywords/skills to add |

---

### Module: `questions/`

| File | Purpose |
|------|---------|
| `questions/generate_bank.yaml` | Generate question set from JD + industry + role type |
| `questions/answer_short.yaml` | Generate short answer (≤100 words) |
| `questions/answer_medium.yaml` | Generate medium answer (100–250 words) |
| `questions/answer_long.yaml` | Generate long STAR answer (250–500 words) |
| `questions/improve_from_edit.yaml` | Update retrieval patterns based on user edits to answers |

---

### Module: `copilot/`

| File | Purpose |
|------|---------|
| `copilot/route_intent.yaml` | Classify user query into intent category |
| `copilot/retrieve_and_respond.yaml` | Generate response using retrieved evidence |
| `copilot/star_response.yaml` | Format evidence into STAR interview answer |
| `copilot/job_fit_analysis.yaml` | Score fit between user profile and job description |
| `copilot/career_advice.yaml` | Generate career guidance grounded in user history |

---

### Module: `ingestion/`

| File | Purpose |
|------|---------|
| `ingestion/extract_entities.yaml` | Extract structured entities from raw text |
| `ingestion/extract_skills.yaml` | Extract skills with confidence from text |
| `ingestion/extract_projects.yaml` | Extract project records from GitHub README / doc |
| `ingestion/normalize_bullets.yaml` | Normalize raw resume bullets into standard format |
| `ingestion/classify_document.yaml` | Determine document type and source category |

---

### Module: `ranking/`

| File | Purpose |
|------|---------|
| `ranking/score_experience_fit.yaml` | Score experience record relevance to a JD |
| `ranking/score_project_fit.yaml` | Score project relevance to a JD |
| `ranking/update_weights.yaml` | Adjust retrieval weights based on outcome signals |

---

## Intent Classification Schema

Used by `copilot/route_intent.yaml`:

```
resume_help         → Route to resume engine
cover_letter_help   → Route to cover letter engine
interview_prep      → Route to STAR / Q&A engine
job_fit_analysis    → Route to fit analysis
career_advice       → Route to career copilot
application_status  → Route to CRM query
knowledge_lookup    → Route to RAG retrieval
```

---

## Variable Reference

All prompts resolve these standard variables at runtime:

| Variable | Source |
|----------|--------|
| `{{system.default_model}}` | `system_config.default_model` |
| `{{system.embedding_model}}` | `system_config.embedding_model` |
| `{{company}}` | Application record |
| `{{position}}` | Application record |
| `{{industry}}` | Application record or detected |
| `{{job_description}}` | Application record |
| `{{experiences_json}}` | Retrieved & ranked experience records |
| `{{projects_json}}` | Retrieved & ranked project records |
| `{{skills_json}}` | Skill records from knowledge graph |

---

## Prompt Versioning Policy

- Increment `version` on ANY change to `system_prompt` or `user_prompt`
- Previous versions must not be deleted — append `_vX_Y_Z` suffix
- `generation_logs` stores the `prompt_name` + `prompt_version` on every call
- Breaking changes to `output_schema` require a new prompt file name

## Prompt Registry (Phase 11.2)

On-disk `prompts/<name>.yaml` files are the **seed/default**. Once a prompt is
*deployed* to the registry it becomes the authoritative, immutable source.

- **Deploy** — `PromptRegistry(session).deploy(name, content_yaml, rationale=...)`
  inserts version `vN+1` and makes it active. Deployed content is **never
  mutated**; editing means deploying a new version. Re-deploying an explicit
  existing version raises `PromptImmutableError`.
- **Resolve** — `PromptLoader(session).load(name)` returns the active version;
  `load(name, version="vK")` pins a specific one. With no session (or a prompt
  never deployed), the loader falls back to the on-disk yaml — so existing
  callers keep working unchanged.
- **Rollback** — `PromptRegistry(session).rollback(name, "vK")` atomically
  switches the active pointer (single-active invariant enforced in the repo).
- **A/B** — `ABTestingService(session).create_prompt_experiment(...)` tags each
  variant with `{prompt_name, version}`; `comparison(experiment_id)` reports
  per-version impressions/conversions/rate. Reuses the Phase 8 A/B machinery.

### Observability & drift

- Metrics (`ats_score`, `retrieval_quality`, `interview_conversion`,
  `embedding_drift`, `prompt_perf`) are recorded append-only via
  `MetricsStore(session).record(kind, value, meta)`.
- `GET /api/v1/observability/drift` reports each kind's baseline (first window
  mean) vs current rolling mean, delta, and `drifting` (|delta| > per-kind
  threshold; override via `system_config` key `drift_threshold::<kind>`).
- `GET /api/v1/observability/metrics?kind=<kind>` returns the raw series.
- Drift **reports only** — any remediation is an approval-gated suggestion (11.4).
