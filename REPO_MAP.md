# Repository Map

An annotated tour of the ACOS tree. For documentation specifically, see
[`docs/INDEX.md`](docs/INDEX.md). For setup and run instructions, see [`README.md`](README.md).

```
ACOS/
├── README.md                  Project overview, setup, run instructions
├── REPO_MAP.md                This file — annotated directory tree
├── CLAUDE.md                  Non-negotiable development rules (enforced)
├── IMPLEMENTATION_ORDER.md    Fixed feature build order
├── GAMEPLAN.md                Original architecture spec (historical; see docs/02_)
├── pyproject.toml             pytest / coverage / pyright config
├── alembic.ini                Alembic migration config (→ database/migrations)
├── acos-backend.spec          PyInstaller spec for the bundled backend binary
│
├── backend/                   ← FastAPI backend (Python)   [see backend/README.md]
│   ├── main.py                App factory; wires routers + middleware + lifespan
│   ├── server_entry.py        PyInstaller entry point (uvicorn on 127.0.0.1:8000)
│   ├── config.py              Pydantic settings (Ollama URL, model names, paths)
│   ├── database.py            SQLAlchemy engine/session, init + seed
│   ├── api/v1/routes/         HTTP endpoints (resume, cover_letter, ats, copilot, …)
│   ├── services/              Business logic — one package per domain:
│   │   ├── resume/            Resume generation, evidence selection, DOCX export
│   │   ├── cover_letter/      Generation, voice modeling, DOCX export
│   │   ├── ats/               Keyword extraction + ATS scoring
│   │   ├── copilot/           Career chat engine
│   │   ├── questions/         Q&A generation
│   │   ├── knowledge_graph/   Knowledge-graph service
│   │   ├── learning/          Outcome ranking
│   │   ├── optimization/      Controlled autonomous loop (A/B, guardrails, evolver)
│   │   ├── rag/               RAG orchestration service
│   │   ├── ollama_client.py   Local LLM client
│   │   └── prompt_loader.py   Loads YAML prompts from backend/prompts/
│   ├── repositories/          Data-access layer (one repo per model; no logic)
│   ├── models/                SQLAlchemy ORM models (the schema in code)
│   ├── rag/                   ChromaDB client, collections, embedder, retriever, reranker
│   ├── ingestion/             File → entities pipeline
│   │   └── parsers/           PDF / DOCX / Markdown / TXT parsers
│   ├── prompts/               Versioned YAML prompt templates (by domain)
│   ├── middleware/            Request timing, etc.
│   └── tests/                 pytest suite
│       ├── unit/              Fast, isolated tests (mirrors source layout)
│       ├── integration/       Service-boundary + API tests
│       └── benchmark/         Performance benchmarks
│
├── frontend/                  ← Tauri + React desktop app   [see frontend/README.md]
│   ├── src/
│   │   ├── pages/             Top-level screens (Resume, ATS, Copilot, Optimization, …)
│   │   ├── components/        Reusable UI (ui/, shared/, per-feature folders)
│   │   ├── layouts/           App shell / navigation
│   │   ├── services/          Typed clients for the backend API
│   │   ├── stores/            Zustand state
│   │   ├── types/             Shared TypeScript types
│   │   └── lib/ utils/        Helpers
│   ├── src-tauri/             Rust desktop shell + sidecar manager
│   │   ├── src/               Rust source (main.rs, lib.rs)
│   │   ├── icons/             App icons
│   │   └── Cargo.toml         Rust dependencies
│   ├── e2e/                   Playwright end-to-end specs
│   ├── package.json           npm scripts: dev / build / tauri
│   └── playwright.config.ts
│
├── database/                  ← Persistence   [see database/README.md]
│   ├── migrations/            Alembic migrations (env.py + versions/)
│   ├── seed/                  Seed data
│   ├── backups/               Backup destination (git-ignored contents)
│   ├── acos.db                SQLite database (git-ignored — runtime data)
│   └── chroma/                ChromaDB store (git-ignored — runtime data)
│
├── scripts/                   ← Tooling   [see scripts/README.md]
│   ├── build_backend.sh       Build the PyInstaller backend sidecar
│   ├── generate_icons.py      Generate Tauri app icons
│   ├── ingestion/             ingest_static_files.py, ingest_github.py
│   ├── maintenance/           reindex_all.py (rebuild vector indexes)
│   └── seed/                  Seed helpers
│
├── docs/                      ← All documentation   [see docs/INDEX.md]
│   ├── 01_… 09_…              Core specs (vision, architecture, schema, prompts, RAG…)
│   ├── *_GUIDE / *_SETUP      Operational guides
│   ├── optimization/          Perf/inference/architecture spike findings + deferred backlog
│   ├── assets/                Doc images
│   ├── adr/                   Architecture Decision Records (ADR-001 … 011)
│   └── superpowers/
│       ├── plans/             One implementation plan per build phase
│       │   └── archive/       Plans for completed phases 0–10
│       └── specs/             Design specs from brainstorming (as needed)
│
├── examples/                  Sample resumes / job descriptions / cover letters
├── .static_files/             Your private source data (git-ignored)
└── LICENSE
```

## How the layers connect

**Backend request flow** (strict, one direction):

```
HTTP request → api/v1/routes → services → repositories → models → SQLite
                                  │
                                  ├→ rag/ (retrieval) ─→ ChromaDB
                                  └→ ollama_client ────→ Ollama (local LLM)
```

Routes contain no business logic; services orchestrate; repositories are the only code
that touches the database. This keeps each layer independently testable — see the test
layout under `backend/tests/`, which mirrors the source tree.

**Desktop flow:** the Tauri Rust shell (`frontend/src-tauri/`) launches the bundled
backend binary as a sidecar and the React UI talks to it over `localhost:8000`.
