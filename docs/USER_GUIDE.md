# ACOS User Guide

AI Career Operating System — local-first career intelligence for job seekers.

## Overview

ACOS helps you:
- Generate tailored, ATS-optimized resumes and cover letters
- Track job applications from first contact to offer
- Get career guidance through a RAG-powered copilot
- Learn from outcomes and improve over time

All data stays on your machine. No cloud APIs are required.

## Getting Started

### Prerequisites

- macOS 10.15+
- [Ollama](https://ollama.ai) installed and running
- Qwen3 8B model: `ollama pull qwen3:8b`
- nomic-embed-text model: `ollama pull nomic-embed-text`

### First Launch

1. Open ACOS from your Applications folder (or from the DMG).
2. The first-run wizard guides you through:
   - Ollama connectivity check (`GET /api/v1/health/ollama`)
   - Model selection (default: `qwen3:8b`)
   - GitHub username (optional, for future integrations)
3. After setup, the main dashboard opens.

If the wizard gets stuck on the Ollama check, see [Troubleshooting](TROUBLESHOOTING.md).

## Ingesting Documents

ACOS becomes more useful as you feed it your professional history. The ingestion
endpoint parses your documents, extracts structured entities, and embeds them into
the local vector store.

**Supported formats:** PDF, DOCX, TXT, Markdown (`.md`)
**File size limit:** 10 MB per file

### Via the API

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@/path/to/resume.pdf"
```

Ingestion is synchronous — the response is returned when processing completes and includes the `ingestion_status` directly. No polling is needed.

### Via the Seed Script

If you already have documents in `.static_files/`, import them all at once:

```bash
source .venv/bin/activate
python scripts/ingestion/ingest_static_files.py
```

This imports your resume, experience bank, cover letters, and historical job
descriptions in one pass. See [Data Import Guide](DATA_IMPORT.md) for details.

## Generating a Resume

1. Go to **Resume Builder** in the sidebar.
2. Paste the full job description text.
3. Click **Generate Resume**.
4. The system retrieves relevant experiences via RAG, generates bullets grounded in
   your profile, and scores the output for ATS compatibility.
5. Download the `.docx` file.

### API

```bash
curl -X POST http://localhost:8000/api/v1/resume/generate \
  -H "Content-Type: application/json" \
  -d '{"job_description": "<paste JD here>"}'
```

### ATS Analysis

To score an existing resume against a job description:

```bash
curl -X POST http://localhost:8000/api/v1/resume/analyze-ats \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "...", "job_description": "..."}'
```

### Confidence Levels

All generated content is tagged with one of three confidence levels:

| Level | Meaning |
|-------|---------|
| `verified` | Traceable to a source document with direct evidence |
| `strong_inference` | Supported by multiple corroborating records |
| `weak_inference` | AI-generated; review before using in applications |

Do not export `weak_inference` bullets without reviewing them first.

## Generating a Cover Letter

1. Go to **Cover Letter** in the sidebar.
2. Enter the job description and target length (100 / 250 / 400 words / full page).
3. Click **Generate**. The voice model (learned from your existing cover letters)
   shapes the tone.

### API

```bash
curl -X POST http://localhost:8000/api/v1/cover-letter/generate \
  -H "Content-Type: application/json" \
  -d '{"job_description": "...", "target_length": 250}'
```

## Tracking Applications

ACOS functions as a lightweight ATS for your own job search.

### Application Statuses

Applications move through a defined lifecycle:

```
draft → applied → phone_screen → interview → final_round → offer
                                                          → rejected
                                                          → withdrawn
```

Each status change is logged with a timestamp for timeline reporting.

### Creating an Application

1. Go to **Applications** in the sidebar.
2. Click **New Application**.
3. Fill in company, position, status, and source.

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "position": "Senior PM",
    "industry": "Technology",
    "status": "applied",
    "date_applied": "2026-06-19"
  }'
```

### Updating Status

```bash
curl -X PUT http://localhost:8000/api/v1/applications/{id} \
  -H "Content-Type: application/json" \
  -d '{"status": "phone_screen"}'
```

## Career Copilot

The copilot is a RAG-grounded question-answering interface powered by `qwen3:8b`.

1. Go to **Copilot** in the sidebar.
2. Ask any career question:
   - "What are my strongest data engineering experiences?"
   - "Draft a STAR answer for conflict resolution."
   - "Summarize my PM experience in three bullet points."
3. The copilot retrieves evidence from your knowledge graph and generates a grounded
   response.
4. Citations are shown below each response.

### API

```bash
curl -X POST http://localhost:8000/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my strongest data engineering experiences?"}'
```

## Learning and Outcome Feedback

ACOS tracks which resumes and strategies correlate with positive outcomes.

### Recording an Outcome

```bash
curl -X POST http://localhost:8000/api/v1/learning/outcome \
  -H "Content-Type: application/json" \
  -d '{"application_id": "...", "outcome": "interview"}'
```

### Viewing the Learning Report

```bash
curl http://localhost:8000/api/v1/learning/report
```

### Re-indexing After New Data

After importing many new documents:

```bash
curl -X POST http://localhost:8000/api/v1/learning/reindex
# or directly:
python scripts/maintenance/reindex_all.py
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `default_model` | `qwen3:8b` | Ollama model used for generation |
| `embedding_model` | `nomic-embed-text` | Embedding model for semantic search |
| `github_username` | — | Used for future GitHub integrations |
| `learning_trigger` | `5` | Applications needed before re-ranking refresh |

### Viewing and Updating Settings

```bash
# View all settings
curl http://localhost:8000/api/v1/settings

# Update a setting
curl -X PUT http://localhost:8000/api/v1/settings/default_model \
  -H "Content-Type: application/json" \
  -d '{"value": "qwen3:14b"}'
```

## Data Storage

All data is stored locally on your machine:

| Path | Contents |
|------|---------|
| `~/.acos/acos.db` | SQLite database (applications, resumes, profiles) |
| `~/.acos/chroma/` | ChromaDB vector store (embeddings) |

No data is transmitted to external services at any time.

## Health Checks

```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# Check Ollama connectivity and model availability
curl http://localhost:8000/api/v1/health/ollama
```

## See Also

- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) — how the system is built
- [Model Setup Guide](MODEL_SETUP.md) — Ollama model configuration
- [Data Import Guide](DATA_IMPORT.md) — importing your professional history
- [Troubleshooting](TROUBLESHOOTING.md) — fixing common issues
