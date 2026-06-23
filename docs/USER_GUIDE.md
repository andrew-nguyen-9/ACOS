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
   - Ollama connectivity check (`GET /api/v1/health/ollama`). If a required model is
     missing, you can **download it from the wizard** with live progress (Phase 13.7) —
     consent-gated, never silent. If Ollama is unreachable you can still *Continue without
     Ollama* into a clearly-degraded mode rather than being blocked.
   - Model selection (default: `qwen3:8b`)
   - GitHub username (optional, for future integrations)
   - **Build your profile (optional, Phase 13.5):** upload résumés / cover letters / job
     history. ACOS extracts your skills (with confidence levels) and your *Career-Voice*
     locally and shows a summary. A starter Career-Voice is clearly labeled **Synthetic**
     until you upload your own writing — it is never presented as your history. This step
     is skippable; you can add documents anytime.
3. After setup, the main dashboard opens.

If the wizard gets stuck on the Ollama check, see [Troubleshooting](TROUBLESHOOTING.md).

### Surfaced intelligence (Phase 13.1–13.4)

The Learning page surfaces **skill ROI** and **global-pattern suggestions** (advisory,
k-anonymous — they inform, they never override your own judgement). The résumé editor
shows non-blocking **strategy hints** for a target job description. The Optimization page
hosts the **prompt-review queue**: candidate prompt versions (some auto-proposed by the
13.6 loop) that a human approves or rejects — nothing is promoted automatically.

### Updates (packaged app, Phase 13.9)

The installed app checks a single signed update channel. When an update is available, a
banner shows the new version and release notes; you click **Update & Relaunch** to apply
it. The update is signature-verified before it installs, and a failed/tampered update
leaves your current version untouched. No other data is sent.

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

## Visual Effects & Showcase Features

ACOS ships a hardware-accelerated, macOS-native interface. Everything below is a
*progressive enhancement* — the app is fully usable with effects turned off.

**Visual Effects tiers** (Settings → Visual Effects):

| Tier | What runs |
|------|-----------|
| **Full** | Animated WebGL background material, cursor focus-glow, success particle bursts, the interview interlocutor |
| **Reduced** | Lighter material, no cursor effects; particles fade in place (no fling) |
| **Off** | Static background, lowest power. Celebrations show a calm flourish; the interview panel still works (audio + cadence meter), just without the WebGL interlocutor |

The effective tier is automatically clamped to **Off** when your display has no WebGL or
when macOS *Reduce Motion* is enabled — accessibility always wins over spectacle.

**Showcase capstones:**

- **Success celebration** — finalizing/exporting a resume that clears the ATS milestone,
  or generating a cover letter, fires a brief GPU particle constellation (Full/Reduced) or
  a tasteful flourish (Off). It's non-blocking and skippable — keep working through it.
- **Cover-letter tone dial** — drag the **Traditional ↔ Bold** slider on a generated cover
  letter. The typography morphs instantly; the letter is quietly regenerated in the chosen
  tone a moment after you stop dragging.
- **Spatial interview panel** — *Interview Prep* places a three-seat virtual panel across
  the stereo field (use headphones for the effect) with a live cadence/pace waveform. Audio
  starts only when you click **Generate Questions** (browsers require a click before playing
  sound).

**Backup, recovery & maintenance** run only on your explicit request — ACOS never performs
destructive maintenance on its own (see Troubleshooting for the recovery/backup commands).

## Career Agent (Phase 15)

ACOS acts as a **controlled-autonomy career agent**: it ranks, recommends, generates, and
simulates — **but it never acts on your behalf**. There is no auto-apply and no recruiter
outreach; every outbound action stays yours (ADR-012). Every recommendation, probability,
and score is shown with its confidence (`verified` / `strong` / `weak`) and the evidence
behind it — never a bare number.

- **Job prioritization** — on the *Applications* page, click **Prioritize jobs**, paste one
  or more job descriptions (separate multiple with a line of `---`), and get a server-ranked
  list: each job tagged with a recommendation, a fit estimate, its confidence, and the
  missing skills behind it. Low-confidence (thin-evidence) rows are de-emphasized and never
  flagged as a "top pick".
- **Application suggestion (Apply / Skip / Tailor)** — click any application to open its
  detail sheet. ACOS recommends Apply, Skip, or Tailor-First, with the suggested resume
  version, cover-letter tone, and interview outlook — each explained and confidence-tagged.
  *Tailor-First* is the safe default whenever fit is anything short of strong. The buttons
  are internal only: **Mark as applied** updates your CRM status; **Tailor in Resume
  Builder** opens the in-app flow. Nothing is ever submitted to a job board.
- **Interview simulation** — *Interview Prep* lets you pick a **recruiter style**
  (balanced / supportive / skeptical / technical) that shapes the questions, type an answer
  to get a **knowledge-graph-grounded evaluation** (which of your real evidence the answer
  did and didn't cover, confidence-tagged), and receive **follow-up questions** that probe
  your answer — all simulated locally.
- **Daily briefing** — the *Dashboard* shows a briefing composed from your data: jobs to
  apply to, skill gaps, resume adjustments, ATS opportunities, and follow-ups due, each
  aligned to your career goal. Jobs that don't fit your goal are flagged *off-goal*. A new
  account with no data sees honest empty sections — never invented jobs or gaps.

## See Also

- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) — how the system is built
- [Model Setup Guide](MODEL_SETUP.md) — Ollama model configuration
- [Data Import Guide](DATA_IMPORT.md) — importing your professional history
- [Troubleshooting](TROUBLESHOOTING.md) — fixing common issues
