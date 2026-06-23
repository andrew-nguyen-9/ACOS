# ACOS — AI Career Operating System

A **local-first** desktop application that helps you generate tailored resumes, cover
letters, and interview answers from your real career history — and continuously learns
from application outcomes to improve over time.

Everything runs on your machine. No career data ever leaves your computer, and after
setup the app works without any cloud AI service or API key.

> **Status:** v1 complete — Phases 0–18 shipped (alpha, 2026-06-23). Further work is
> demand-driven; see [`docs/v2/ROADMAP.md`](docs/v2/ROADMAP.md).

> **One deliberate network exception:** the packaged app checks a single signed update
> channel over TLS — a version check plus the signature-verified update download, nothing
> else (no telemetry, no identity, no career data). See
> [`docs/adr/ADR-011-background-auto-update-network-boundary.md`](docs/adr/ADR-011-background-auto-update-network-boundary.md).

> **New here?**
> - **Just want to run the app?** → [Install the app](#install-the-app-end-users) below.
> - **Building or contributing?** → [`REPO_MAP.md`](REPO_MAP.md) for the layout and
>   [`docs/INDEX.md`](docs/INDEX.md) for the full documentation map.

---

## What it does

| Capability | Description |
|------------|-------------|
| **Document ingestion** | Parse résumés, job descriptions, and project docs (PDF/DOCX/Markdown/TXT) into a structured knowledge graph. |
| **Resume engine** | Generate ATS-optimized resumes from verified evidence, with confidence levels on every claim. |
| **Cover letter engine** | Draft cover letters that match your voice, learned from past writing. |
| **ATS scoring** | Score resumes against a job description and surface missing keywords. |
| **Career copilot** | Chat over your own career history with retrieval-augmented answers. |
| **Q&A engine** | Generate and answer application/interview questions from evidence. |
| **Outcome learning** | Rank and learn from application outcomes to improve future generations. |
| **Controlled optimization** | A guarded, autonomous loop that A/B-tests prompt variants against measurable gates (see [`docs/OPTIMIZATION_SYSTEM.md`](docs/OPTIMIZATION_SYSTEM.md)). |
| **Career agent** | Ranks jobs, recommends Apply/Skip/Tailor, simulates interviews (recruiter personas + KG-grounded answer eval), and composes a goal-aligned daily briefing. **Recommends, never acts** — no auto-apply, no recruiter outreach ([ADR-012](docs/adr/ADR-012-controlled-autonomy-boundary.md)). |
| **Showcase-grade UI** | Hardware-accelerated, macOS-native interface — one WebGL material, success-particle celebrations, a quantum cover-letter tone dial, and a spatial-audio interview panel. All performance-gated (60 FPS) and fully degradable to a calm static app (see [`docs/FRONTEND_DESIGN_SYSTEM.md`](docs/FRONTEND_DESIGN_SYSTEM.md)). |

A core rule of the system: **no hallucinated facts.** Every generated statement traces
back to a source record with a confidence level (`verified` / `strong_inference` /
`weak_inference`). See [ADR-006](docs/adr/ADR-006-evidence-confidence-system.md).

---

## Install the app (end users)

ACOS ships as a single macOS **`.dmg`**. You only need **two** things:

1. **The ACOS DMG** — if a packaged build has been published, download it; otherwise
   build it yourself in one command: `scripts/build_dmg.sh` (see [Packaging](#packaging)).
2. **[Ollama](https://ollama.ai)** — the local AI engine. Install it, then pull the models:

   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

Then:

1. Open the DMG and drag **ACOS** into **Applications**.
2. **First launch (one-time):** the alpha DMG is **unsigned**, so macOS Gatekeeper will
   block a normal double-click. Right-click **ACOS** → **Open** → **Open**. macOS
   remembers the choice; every launch after is a normal double-click.
   _(Equivalent terminal one-liner: `xattr -dr com.apple.quarantine /Applications/ACOS.app`.)_
3. The first-run wizard checks Ollama, helps you pull any missing model, and walks you
   through importing your first document. Done.

Everything after that runs fully offline. See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
for day-to-day usage and [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) if launch
misbehaves.

> Why unsigned? Signing requires a paid Apple Developer ID; the alpha is distributed
> unsigned by design ([ADR-020](docs/adr/ADR-020-alpha-distribution-update-rollout.md)).
> The right-click-Open step is the standard, safe way to run it.

---

## Technology stack (locked)

| Layer | Technology |
|-------|-----------|
| Desktop shell | Tauri v2 (Rust) — manages the backend as a sidecar process |
| Frontend | React 18 + TypeScript + TailwindCSS + Zustand |
| Backend | Python 3.11+ + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Database | SQLite (via SQLAlchemy), migrated with Alembic |
| Vector store | ChromaDB (`PersistentClient`) |
| LLM | Ollama + `qwen3:8b` |
| Embeddings | Ollama + `nomic-embed-text` |
| Testing | pytest (backend), Playwright (frontend E2E) |
| Type checking | pyright (backend), tsc (frontend) |

The rationale for each choice lives in [`docs/adr/`](docs/adr/).

---

## Architecture at a glance

```
┌──────────────────────────────────────────────────────────┐
│  Tauri v2 desktop shell (Rust)                            │
│   • React 18 + TypeScript UI                              │
│   • Rust sidecar manager starts/stops the backend         │
└───────────────────────┬───────────────────────────────────┘
                        │ HTTP — localhost:8000
┌───────────────────────▼───────────────────────────────────┐
│  FastAPI backend (Python 3.11)                            │
│                                                            │
│   api/v1/routes  →  services  →  repositories  →  models   │
│                         │                                  │
│                         ├─ rag/        (ChromaDB retrieval)│
│                         ├─ ingestion/  (file → entities)   │
│                         └─ ollama_client (local LLM)       │
└───────────────────────┬───────────────────────────────────┘
                        │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   SQLite (acos.db)               ChromaDB (vector store)
```

The backend follows a strict layering: **routes → services → repositories → models.**
Routes never touch the database directly; they call services, which call repositories.
See [`docs/ARCHITECTURE_OVERVIEW.md`](docs/ARCHITECTURE_OVERVIEW.md) for the full picture.

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ and npm
- **Rust** toolchain (for Tauri) — https://rustup.rs
- **Ollama** — https://ollama.ai — with the required models pulled:

  ```bash
  ollama pull qwen3:8b
  ollama pull nomic-embed-text
  ```

  Full model guidance: [`docs/MODEL_SETUP.md`](docs/MODEL_SETUP.md).

---

## Quick start

### 1. Backend

```bash
# from repo root
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# apply database migrations
alembic upgrade head

# run the API (http://127.0.0.1:8000, docs at /docs)
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install

# web dev server (browser)
npm run dev

# full desktop app (Tauri) — requires the backend running or bundled
npm run tauri dev
```

### 3. Load your data

Place source files under `.static_files/` (git-ignored), then run the ingestion scripts:

```bash
python scripts/ingestion/ingest_static_files.py   # résumés, JDs, projects
python scripts/ingestion/ingest_github.py          # GitHub repositories
```

See [`docs/DATA_IMPORT.md`](docs/DATA_IMPORT.md) for the import workflow and
[`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for day-to-day usage.

---

## Testing & quality gates

```bash
# Backend: unit + integration, with coverage (gate: ≥90%)
pytest

# Backend: type checking
pyright

# Frontend: type checking
cd frontend && npx tsc --noEmit

# Frontend: end-to-end (Playwright)
cd frontend && npx playwright test
```

Coverage and pytest configuration live in [`pyproject.toml`](pyproject.toml); the
coverage gate is `fail_under = 90`.

---

## Packaging

The backend is bundled into a standalone binary with PyInstaller
(`backend/server_entry.py` is the entry point), embedded as a Tauri sidecar, and shipped
as a macOS DMG. **One command builds the whole thing:**

```bash
scripts/build_dmg.sh
```

Output: `frontend/src-tauri/target/release/bundle/dmg/ACOS_<version>_<arch>.dmg`.

Full build, signing/notarization, and release-verification details (including the
unsigned-alpha fallback) are in [`docs/PACKAGING.md`](docs/PACKAGING.md).

---

## Repository layout

| Path | Purpose |
|------|---------|
| [`backend/`](backend/README.md) | FastAPI app: routes, services, repositories, models, RAG, ingestion |
| [`frontend/`](frontend/README.md) | Tauri + React + TypeScript desktop UI |
| [`database/`](database/README.md) | SQLite DB, Alembic migrations, seed data |
| [`scripts/`](scripts/README.md) | Ingestion, maintenance, and build scripts |
| [`docs/`](docs/INDEX.md) | Product, architecture, schema, ADRs, and phase plans |
| `.static_files/` | Your private source data (git-ignored) |
| `examples/` | Sample resumes / job descriptions / cover letters |

A fuller, annotated tree is in [`REPO_MAP.md`](REPO_MAP.md).

---

## Working in this repo (for contributors & AI agents)

Development is governed by [`CLAUDE.md`](CLAUDE.md) — the non-negotiable rules:
TDD before implementation, type checking, no hallucinated content, and reading the docs
before building. **v1 (Phases 0–18) is complete**; frozen per-phase history lives under
[`docs/v1/plans/`](docs/v1/plans/). New work is demand-driven and batched through
[`docs/BACKLOG.md`](docs/BACKLOG.md) into v2 phases — see
[`docs/v2/ROADMAP.md`](docs/v2/ROADMAP.md).

---

## License

See [`LICENSE`](LICENSE).
