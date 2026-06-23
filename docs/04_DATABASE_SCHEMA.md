# ACOS Database Schema

## Design Principles

- SQLite is the single source of truth for structured data
- ChromaDB holds vector embeddings only — never canonical records
- Every generated statement must link to one or more `evidence_id` values
- All tables use UUID primary keys (`TEXT` in SQLite)
- `created_at` / `updated_at` on every mutable table
- Confidence levels: `verified | strong_inference | weak_inference`

---

## Migration Strategy

Migrations live in `database/migrations/` as numbered SQL files:

```
database/migrations/
  0001_create_experiences.sql
  0002_create_projects.sql
  0003_create_skills.sql
  ...
```

Run via `scripts/maintenance/run_migrations.py`. Applied migrations recorded in `schema_migrations` table.

---

## Tables

### schema_migrations

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version       TEXT PRIMARY KEY,
    applied_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### experiences

```sql
CREATE TABLE IF NOT EXISTS experiences (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    title            TEXT NOT NULL,
    company          TEXT NOT NULL,
    employment_type  TEXT NOT NULL CHECK (employment_type IN (
                         'full_time', 'part_time', 'contract', 'internship', 'freelance'
                     )),
    start_date       TEXT NOT NULL,   -- ISO 8601 YYYY-MM-DD
    end_date         TEXT,            -- NULL means current position
    is_current       INTEGER NOT NULL DEFAULT 0,
    location         TEXT,
    description      TEXT,
    source           TEXT NOT NULL CHECK (source IN (
                         'manual', 'resume_import', 'linkedin', 'document_import'
                     )),
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_experiences_company ON experiences(company);
CREATE INDEX idx_experiences_start_date ON experiences(start_date);
```

---

### experience_bullets

Each experience has N bullets. Bullets are individually confidence-rated.

```sql
CREATE TABLE IF NOT EXISTS experience_bullets (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    experience_id    TEXT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    bullet_text      TEXT NOT NULL,
    order_index      INTEGER NOT NULL DEFAULT 0,
    confidence_level TEXT NOT NULL CHECK (confidence_level IN (
                         'verified', 'strong_inference', 'weak_inference'
                     )),
    evidence_ids     TEXT NOT NULL DEFAULT '[]',  -- JSON array of document IDs
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_bullets_experience_id ON experience_bullets(experience_id);
```

---

### projects

```sql
CREATE TABLE IF NOT EXISTS projects (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name             TEXT NOT NULL,
    description      TEXT,
    industry         TEXT,
    repository_url   TEXT,
    tech_stack       TEXT NOT NULL DEFAULT '[]',   -- JSON array
    start_date       TEXT,
    end_date         TEXT,
    is_ongoing       INTEGER NOT NULL DEFAULT 0,
    confidence_level TEXT NOT NULL CHECK (confidence_level IN (
                         'verified', 'strong_inference', 'weak_inference'
                     )),
    source           TEXT NOT NULL CHECK (source IN (
                         'manual', 'github', 'document_import', 'claude_export'
                     )),
    source_url       TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### skills

```sql
CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category    TEXT NOT NULL CHECK (category IN (
                    'programming', 'data', 'domain', 'soft', 'tool', 'methodology'
                )),
    proficiency TEXT NOT NULL CHECK (proficiency IN (
                    'exposure', 'beginner', 'intermediate', 'advanced', 'expert'
                )),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_name ON skills(name COLLATE NOCASE);
```

---

### skill_evidence

```sql
CREATE TABLE IF NOT EXISTS skill_evidence (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    skill_id         TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    source_type      TEXT NOT NULL CHECK (source_type IN (
                         'experience', 'project', 'github', 'document', 'self_reported'
                     )),
    source_id        TEXT NOT NULL,   -- FK to the source entity (experience_id, project_id, etc.)
    evidence_text    TEXT NOT NULL,
    confidence_level TEXT NOT NULL CHECK (confidence_level IN (
                         'verified', 'strong_inference', 'weak_inference'
                     )),
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_skill_evidence_skill_id ON skill_evidence(skill_id);
CREATE INDEX idx_skill_evidence_source ON skill_evidence(source_type, source_id);
```

---

### experience_skills (join table)

```sql
CREATE TABLE IF NOT EXISTS experience_skills (
    experience_id TEXT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    skill_id      TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (experience_id, skill_id)
);
```

---

### project_skills (join table)

```sql
CREATE TABLE IF NOT EXISTS project_skills (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    skill_id   TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, skill_id)
);
```

---

### resume_templates

```sql
CREATE TABLE IF NOT EXISTS resume_templates (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name             TEXT NOT NULL,
    target_industry  TEXT,
    layout_type      TEXT NOT NULL CHECK (layout_type IN (
                         'single_column', 'two_column', 'hybrid'
                     )),
    template_json    TEXT NOT NULL DEFAULT '{}',  -- JSON structure definition
    is_default       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### writing_profiles

Learned from historical cover letters to capture voice and tone.

```sql
CREATE TABLE IF NOT EXISTS writing_profiles (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    tone_descriptors    TEXT NOT NULL DEFAULT '[]',    -- JSON: ["direct", "professional"]
    structure_patterns  TEXT NOT NULL DEFAULT '[]',    -- JSON: opening/closing patterns
    vocabulary_patterns TEXT NOT NULL DEFAULT '{}',    -- JSON: preferred vocab
    sample_sentences    TEXT NOT NULL DEFAULT '[]',    -- JSON: exemplar sentences
    source_doc_ids      TEXT NOT NULL DEFAULT '[]',    -- JSON: document IDs used to build profile
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### applications

```sql
CREATE TABLE IF NOT EXISTS applications (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    company          TEXT NOT NULL,
    position         TEXT NOT NULL,
    industry         TEXT,
    job_description  TEXT,
    job_url          TEXT,
    status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                         'draft', 'applied', 'phone_screen', 'interview',
                         'final_round', 'offer', 'rejected', 'withdrawn'
                     )),
    date_applied     TEXT,
    salary_min       INTEGER,
    salary_max       INTEGER,
    currency         TEXT NOT NULL DEFAULT 'USD',
    work_arrangement TEXT CHECK (work_arrangement IN ('remote', 'hybrid', 'onsite')),
    source           TEXT CHECK (source IN (
                         'linkedin', 'indeed', 'referral', 'direct', 'recruiter', 'other'
                     )),
    recruiter_name   TEXT,
    recruiter_email  TEXT,
    notes            TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_date_applied ON applications(date_applied);
CREATE INDEX idx_applications_company ON applications(company);
```

---

### application_timeline

Ordered log of status transitions for an application.

```sql
CREATE TABLE IF NOT EXISTS application_timeline (
    id             TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type     TEXT NOT NULL CHECK (event_type IN (
                       'status_change', 'note_added', 'document_attached',
                       'interview_scheduled', 'outcome_recorded'
                   )),
    from_status    TEXT,
    to_status      TEXT,
    note           TEXT,
    event_date     TEXT NOT NULL DEFAULT (datetime('now')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_timeline_application ON application_timeline(application_id);
```

---

### resumes

```sql
CREATE TABLE IF NOT EXISTS resumes (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    application_id   TEXT REFERENCES applications(id) ON DELETE SET NULL,
    template_id      TEXT REFERENCES resume_templates(id) ON DELETE SET NULL,
    name             TEXT NOT NULL,
    content_json     TEXT NOT NULL DEFAULT '{}',  -- structured resume content
    file_path        TEXT,
    ats_score        REAL,
    word_count       INTEGER,
    page_count       INTEGER NOT NULL DEFAULT 1,
    is_master        INTEGER NOT NULL DEFAULT 0,  -- the canonical master resume
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_resumes_application ON resumes(application_id);
```

---

### cover_letters

```sql
CREATE TABLE IF NOT EXISTS cover_letters (
    id                 TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    application_id     TEXT REFERENCES applications(id) ON DELETE SET NULL,
    writing_profile_id TEXT REFERENCES writing_profiles(id) ON DELETE SET NULL,
    content_text       TEXT,
    word_count         INTEGER,
    length_target      TEXT NOT NULL DEFAULT '250' CHECK (length_target IN (
                           '100', '250', '400', 'full_page', 'custom'
                       )),
    file_path          TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_cover_letters_application ON cover_letters(application_id);
```

---

### questions

```sql
CREATE TABLE IF NOT EXISTS questions (
    id                TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    question_template TEXT NOT NULL,
    industry          TEXT,
    category          TEXT NOT NULL CHECK (category IN (
                          'behavioral', 'technical', 'situational',
                          'motivational', 'cultural', 'role_specific'
                      )),
    length_target     TEXT NOT NULL DEFAULT 'medium' CHECK (length_target IN (
                          'short', 'medium', 'long'
                      )),
    variables         TEXT NOT NULL DEFAULT '[]',  -- JSON: ["{{company}}", "{{position}}"]
    source            TEXT NOT NULL CHECK (source IN (
                          'manual', 'job_description', 'generated', 'import'
                      )),
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_questions_category ON questions(category);
CREATE INDEX idx_questions_industry ON questions(industry);
```

---

### answers

```sql
CREATE TABLE IF NOT EXISTS answers (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    question_id      TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    application_id   TEXT REFERENCES applications(id) ON DELETE SET NULL,
    original_answer  TEXT NOT NULL,
    edited_answer    TEXT,
    diff_summary     TEXT,
    confidence_level TEXT NOT NULL CHECK (confidence_level IN (
                         'verified', 'strong_inference', 'weak_inference'
                     )),
    evidence_ids     TEXT NOT NULL DEFAULT '[]',  -- JSON array
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_answers_question ON answers(question_id);
CREATE INDEX idx_answers_application ON answers(application_id);
```

---

### documents

Tracks all ingested files — source documents, not generated outputs.

```sql
CREATE TABLE IF NOT EXISTS documents (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    filename         TEXT NOT NULL,
    original_path    TEXT NOT NULL,
    file_type        TEXT NOT NULL CHECK (file_type IN (
                         'pdf', 'docx', 'txt', 'md', 'json', 'github_repo'
                     )),
    file_size_bytes  INTEGER,
    checksum_sha256  TEXT,
    source_type      TEXT NOT NULL CHECK (source_type IN (
                         'resume', 'cover_letter', 'job_description',
                         'github', 'claude_export', 'answer_bank', 'other'
                     )),
    ingestion_status TEXT NOT NULL DEFAULT 'pending' CHECK (ingestion_status IN (
                         'pending', 'processing', 'complete', 'failed', 'skipped'
                     )),
    metadata_json    TEXT NOT NULL DEFAULT '{}',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at     TEXT
);

CREATE INDEX idx_documents_status ON documents(ingestion_status);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE UNIQUE INDEX idx_documents_checksum ON documents(checksum_sha256) WHERE checksum_sha256 IS NOT NULL;
```

---

### ingestion_logs

```sql
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    stage       TEXT NOT NULL CHECK (stage IN (
                    'parse', 'normalize', 'extract_entities', 'embed', 'link_graph'
                )),
    status      TEXT NOT NULL CHECK (status IN ('success', 'failure', 'skipped')),
    message     TEXT,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ingestion_logs_document ON ingestion_logs(document_id);
```

---

### generation_logs

```sql
CREATE TABLE IF NOT EXISTS generation_logs (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    generation_type  TEXT NOT NULL CHECK (generation_type IN (
                         'resume', 'cover_letter', 'answer', 'copilot', 'ats_analysis'
                     )),
    application_id   TEXT REFERENCES applications(id) ON DELETE SET NULL,
    prompt_name      TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    model            TEXT NOT NULL,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    duration_ms      INTEGER,
    success          INTEGER NOT NULL DEFAULT 1,
    error_message    TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_generation_logs_type ON generation_logs(generation_type);
CREATE INDEX idx_generation_logs_application ON generation_logs(application_id);
```

---

### knowledge_graph_nodes

```sql
CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    node_type   TEXT NOT NULL CHECK (node_type IN (
                    'experience', 'skill', 'project', 'company',
                    'application', 'document', 'answer'
                )),
    entity_id   TEXT NOT NULL,   -- FK to the source table
    label       TEXT NOT NULL,
    properties  TEXT NOT NULL DEFAULT '{}',  -- JSON
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_kg_nodes_type ON knowledge_graph_nodes(node_type);
CREATE INDEX idx_kg_nodes_entity ON knowledge_graph_nodes(node_type, entity_id);
```

---

### knowledge_graph_edges

```sql
CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    from_node_id     TEXT NOT NULL REFERENCES knowledge_graph_nodes(id) ON DELETE CASCADE,
    to_node_id       TEXT NOT NULL REFERENCES knowledge_graph_nodes(id) ON DELETE CASCADE,
    relationship     TEXT NOT NULL CHECK (relationship IN (
                         'has_skill', 'uses_technology', 'worked_at', 'produced',
                         'evidenced_by', 'applied_to', 'answered_for',
                         'resulted_in', 'related_to'
                     )),
    weight           REAL NOT NULL DEFAULT 1.0,
    properties       TEXT NOT NULL DEFAULT '{}',  -- JSON
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_kg_edges_from ON knowledge_graph_edges(from_node_id);
CREATE INDEX idx_kg_edges_to ON knowledge_graph_edges(to_node_id);
CREATE INDEX idx_kg_edges_relationship ON knowledge_graph_edges(relationship);
```

---

### outcome_signals

Learning signals used to re-rank experiences, projects, and templates.

```sql
CREATE TABLE IF NOT EXISTS outcome_signals (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    application_id  TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    resume_id       TEXT REFERENCES resumes(id) ON DELETE SET NULL,
    signal_type     TEXT NOT NULL CHECK (signal_type IN (
                        'no_response', 'rejected', 'phone_screen',
                        'interview', 'final_round', 'offer', 'accepted'
                    )),
    signal_weight   REAL NOT NULL,   -- from GAMEPLAN weights
    template_used   TEXT,
    ats_score       REAL,
    industry        TEXT,
    position_type   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_outcome_signals_application ON outcome_signals(application_id);
CREATE INDEX idx_outcome_signals_type ON outcome_signals(signal_type);
```

---

### system_config

```sql
CREATE TABLE IF NOT EXISTS system_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Default values inserted at migration time
INSERT INTO system_config (key, value, description) VALUES
    ('default_model', 'qwen3:8b', 'Default Ollama model for generation'),
    ('embedding_model', 'nomic-embed-text', 'Ollama model for embeddings'),
    ('learning_trigger_count', '5', 'Applications before learning refresh'),
    ('ats_keyword_weight', '0.35', 'ATS scoring: keyword match weight'),
    ('ats_skill_weight', '0.25', 'ATS scoring: skill match weight'),
    ('ats_experience_weight', '0.20', 'ATS scoring: experience match weight'),
    ('ats_industry_weight', '0.10', 'ATS scoring: industry match weight'),
    ('ats_education_weight', '0.10', 'ATS scoring: education match weight');
```

---

### signals (Phase 12.10)

Normalized feedback-loop events the flywheel (12.11 ROI, 12.13 prompt evolution)
consumes. Every signal traces to its source record(s) via `source_json` (no orphan
signals). `tenant_id` made NOT NULL + FK in 12.14.

```sql
CREATE TABLE IF NOT EXISTS signals (
    id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    tenant_id    TEXT NOT NULL REFERENCES tenants(id),   -- 12.14
    entity_type  TEXT NOT NULL,            -- 'application' | 'skill' | 'template'
    entity_id    TEXT NOT NULL,
    signal_type  TEXT NOT NULL,            -- 'skill_used' | 'ats_score' | outcome ladder
    value        REAL NOT NULL,
    weight       REAL NOT NULL DEFAULT 1.0,
    source_json  JSON NOT NULL,            -- {"table": ..., "ids": [...]}
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_signals_tenant_id ON signals(tenant_id);
CREATE INDEX idx_signals_entity ON signals(entity_type, entity_id);
```

---

### tenants (Phase 12.14)

Local career profiles (ADR-008: one DB, enforced `tenant_id`, no auth). 12.14 adds a
NOT NULL `tenant_id` FK to `tenants(id)` on every tenant-owned table (experiences,
projects, skills, applications, resumes, writing_profiles, questions, answers,
documents, generation_logs, knowledge_graph_nodes, knowledge_graph_edges,
outcome_signals, metrics, memory, signals); existing rows backfilled to a `default`
tenant. System/template/optimization tables stay shared.

```sql
CREATE TABLE IF NOT EXISTS tenants (
    id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name       TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO tenants (id, name) VALUES ('default', 'default');
```

---

### global_patterns (Phase 12.15)

Content-free cross-tenant aggregate store (ADR-009). Abstract fields + a tenant COUNT
only — **no** `tenant_id`, no raw text, no embeddings. Populated only through the
k-anonymity gate (k ≥ 5 contributing tenants).

```sql
CREATE TABLE IF NOT EXISTS global_patterns (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    pattern_type  TEXT NOT NULL,           -- 'skill_roi'
    industry      TEXT NOT NULL,
    key           TEXT NOT NULL,           -- abstract label (skill / section)
    value         REAL NOT NULL,           -- aggregate (e.g. mean ROI)
    metric        TEXT NOT NULL DEFAULT 'interview_lift',
    tenant_count  INTEGER NOT NULL,        -- count, never ids
    confidence    TEXT NOT NULL DEFAULT 'strong_inference',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_global_patterns_lookup ON global_patterns(pattern_type, industry);
```

> Phase 12.13 (adaptive prompt evolution) adds no new table — it extends the existing
> `prompt_versions` (11.2) with candidate rows + an `is_active` pointer, audited via
> `optimization_logs`.

---

## Outcome Signal Weights

| Signal       | Weight |
|-------------|--------|
| no_response | 0      |
| rejected    | 0      |
| phone_screen| 3      |
| interview   | 5      |
| final_round | 15     |
| offer       | 25     |
| accepted    | 30     |

---

## Entity Relationship Summary

```
experiences ──< experience_bullets
experiences >──< skills (via experience_skills)
projects    >──< skills (via project_skills)
skills ──< skill_evidence

applications ──< application_timeline
applications ──> resumes
applications ──> cover_letters
applications ──< answers
applications ──< outcome_signals

questions ──< answers

documents ──< ingestion_logs

knowledge_graph_nodes >──< knowledge_graph_nodes (via knowledge_graph_edges)
```
