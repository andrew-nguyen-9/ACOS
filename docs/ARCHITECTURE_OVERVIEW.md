# ACOS Architecture Overview

AI Career Operating System — technical architecture reference.

## System Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Tauri v2 Desktop Shell (macOS)                             │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │  React 18 Frontend   │  │  Rust Sidecar Manager     │   │
│  │  TypeScript          │  │  (starts/stops backend)   │   │
│  │  TailwindCSS         │  └───────────────────────────┘   │
│  │  Zustand state       │                                   │
│  └──────────┬───────────┘                                   │
│             │ HTTP / localhost:8000                          │
└─────────────┼───────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11 — PyInstaller binary)         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  API Routes (/api/v1)                               │    │
│  │  /health  /ingest  /resume  /cover-letter           │    │
│  │  /applications  /learning  /copilot  /settings      │    │
│  └─────────────┬───────────────────────┬───────────────┘    │
│                │                       │                     │
│  ┌─────────────▼──────────┐  ┌────────▼────────────────┐   │
│  │  Service Layer         │  │  RAG Pipeline            │   │
│  │  resume.generator      │  │  Embedder (nomic)        │   │
│  │  cover_letter.gen      │  │  ChromaDB (10 cols)      │   │
│  │  ats.scorer            │  │  BM25 Reranker           │   │
│  │  copilot.engine        │  │  Retriever               │   │
│  │  learning.ranker       │  └────────────┬────────────┘    │
│  └─────────────┬──────────┘               │                 │
│                │                          │                  │
│  ┌─────────────▼──────────────────────────▼──────────────┐  │
│  │  SQLite (acos.db)   +   ChromaDB (chroma/)            │  │
│  │  SQLAlchemy 2.0         PersistentClient              │  │
│  │  Alembic migrations     10 collections                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
              │ HTTP / localhost:11434
┌─────────────▼───────────────────────────────────────────────┐
│  Ollama (user-installed, runs separately)                    │
│  qwen3:8b  (generation)  nomic-embed-text  (embeddings)      │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Desktop shell | Tauri v2 | macOS; Rust sidecar manages backend lifecycle |
| Frontend | React 18 + TypeScript | TailwindCSS for styling; Zustand for state |
| Backend | Python 3.11 + FastAPI | Packaged with PyInstaller for distribution |
| ORM | SQLAlchemy 2.0 | Async-compatible; Alembic for migrations |
| Database | SQLite | Stored at `~/.acos/acos.db` |
| Vector store | ChromaDB (PersistentClient) | Stored at `~/.acos/chroma/` |
| LLM | Ollama + `qwen3:8b` | All inference is local; no cloud calls |
| Embeddings | Ollama + `nomic-embed-text` | 768-dimensional vectors |
| E2E tests | Playwright | Full golden-path coverage |

## Key Design Decisions

### Local-First

No cloud APIs. All LLM calls go to Ollama on `localhost:11434`. ChromaDB and SQLite
are stored in `~/.acos/`. The application is fully functional with no internet
connection after initial setup.

### Confidence System

Every piece of generated content is tagged with one of three evidence levels:

- `verified` — traceable to a source document with direct evidence
- `strong_inference` — supported by multiple corroborating records
- `weak_inference` — model-generated; requires user review before export

This prevents hallucination from propagating into job applications. See
`docs/adr/ADR-006-evidence-confidence-system.md` for the full rationale.

### RAG Pipeline with BM25 Reranking

Semantic search (via ChromaDB HNSW) is combined with BM25 keyword scoring to
improve retrieval precision for domain-specific terms (job titles, technology stacks,
acronyms). The two-stage pipeline:

1. **Recall** — ChromaDB HNSW retrieves the top-K candidates by cosine similarity.
2. **Rerank** — BM25 re-scores candidates against the query; results are merged
   using reciprocal rank fusion.

This hybrid approach outperforms pure semantic search on specialized vocabulary.

### Outcome Learning

Every application status change emits an `OutcomeSignal`. The `OutcomeRanker`
tracks which resume templates and ATS scores correlate with positive outcomes
(phone screen, interview, offer), feeding back into retrieval weight adjustments.
Re-indexing is triggered via `POST /api/v1/learning/reindex`.

### PyInstaller Sidecar

The Python backend is frozen into a single binary by PyInstaller. Tauri v2 manages
its lifecycle as an `externalBin` — the backend starts when the Tauri window opens
and is killed when the window closes. In development, the backend can be started
manually with `uvicorn backend.main:app --port 8000`.

## API Surface

All routes are versioned under `/api/v1`.

| Route | Method(s) | Purpose |
|-------|-----------|---------|
| `/health` | GET | Backend liveness check |
| `/health/ollama` | GET | Ollama connectivity and model availability |
| `/ingest` | POST | Upload a document (multipart file); returns ingestion_status synchronously |
| `/resume/generate` | POST | Generate a tailored resume from a JD |
| `/resume/analyze-ats` | POST | Score a resume against a job description |
| `/cover-letter/generate` | POST | Generate a cover letter from a JD |
| `/applications` | GET, POST | List or create applications |
| `/applications/{id}` | GET, PUT, DELETE | Read, update, or delete an application |
| `/learning/outcome` | POST | Record an outcome signal |
| `/learning/report` | GET | View outcome analytics |
| `/learning/reindex` | POST | Re-embed all documents |
| `/copilot/chat` | POST | Send a message to the RAG copilot |
| `/settings` | GET | View all system settings |
| `/settings/{key}` | PUT | Update a setting by key |

## Database Schema Summary

Full schema: `docs/04_DATABASE_SCHEMA.md`

| Table(s) | Purpose |
|----------|---------|
| `documents`, `ingestion_log` | Raw files and parse status |
| `experiences`, `skills`, `projects` | Structured profile data |
| `knowledge_graph_nodes`, `knowledge_graph_edges` | Knowledge graph topology |
| `resumes`, `resume_sections`, `resume_bullets` | Generated resume artifacts |
| `applications`, `timeline_events` | CRM / application tracking |
| `outcome_signals` | Learning feedback from application outcomes |
| `system_config` | Key-value settings store |
| `questions`, `answers` | Q&A engine |

## ChromaDB Collections

Ten collections defined in `backend/rag/collections.py`:

| Collection | Contents |
|------------|---------|
| `acos_experiences` | Work experience embeddings |
| `acos_projects` | Project descriptions |
| `acos_skills` | Skill descriptions and context |
| `acos_resumes` | Generated resume content |
| `acos_cover_letters` | Generated and imported cover letters |
| `acos_questions` | Question bank entries |
| `acos_answers` | Historical Q&A answers |
| `acos_job_descriptions` | Parsed job description entities |
| `acos_github` | GitHub repository README content |
| `acos_claude_exports` | Claude conversation exports |

## Data Flow: Resume Generation

```
User submits JD text
       │
       ▼
JD Analysis Service — extracts required skills, titles, keywords
       │
       ▼
RAG Retrieval — queries ChromaDB collections:
  experiences + skills + projects + resumes
       │
       ▼
BM25 Reranker — re-scores candidates against JD keywords
       │
       ▼
Ollama (qwen3:8b) — generates resume bullets from retrieved evidence
       │
       ▼
ATS Scorer — computes keyword match score
       │
       ▼
Response — resume JSON with confidence levels + ATS score
```

## Security Model

- All file ingestion validates paths against an allowlist; symlink traversal is blocked
- Filenames with `..` or `/` are rejected (see `backend/utils/sanitize_filename.py`)
- File size cap: 10 MB for local files, 50 KB for GitHub README URLs (OOM prevention)
- No plaintext secrets; Ollama connection requires no authentication (localhost only)
- No data is transmitted to any external service during operation

## See Also

- `docs/adr/` — Architecture Decision Records
- `docs/04_DATABASE_SCHEMA.md` — full SQLite schema
- `docs/06_RAG_DESIGN.md` — RAG pipeline design details
- `docs/07_PLUGIN_ORCHESTRATION.md` — feature implementation checklist
