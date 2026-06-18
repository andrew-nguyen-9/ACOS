# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all foundational infrastructure — config, logging, SQLAlchemy models, Alembic migrations, repository layer, ChromaDB integration, Ollama client, FastAPI skeleton, and frontend scaffold — with ≥90% test coverage, before any business logic is written.

**Architecture:** Sync SQLAlchemy 2.0 ORM with SQLite; sessions are injected via FastAPI `Depends(get_session)`; ChromaDB runs in-process via `PersistentClient`; Ollama is called over HTTP via `httpx`. All models use UUID TEXT primary keys. JSON columns stored as SQLAlchemy `JSON` type (SQLite TEXT under the hood).

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Alembic 1.14, Pydantic v2, ChromaDB 0.5, httpx 0.27, pytest 8, React 18, TypeScript 5, Vite 5, TailwindCSS 3, Tauri v2

## Global Constraints

- Python ≥ 3.11 (uses `str | None` union syntax)
- No `Any` types without justification (pyright strict)
- All primary keys: `String(32)` UUID hex (no hyphens), generated via `uuid.uuid4().hex`
- Timestamps: ISO 8601 string `String(26)`, e.g. `"2026-06-18T12:00:00.000000"`
- JSON columns: SQLAlchemy `JSON` type, Python default is a lambda returning `list` or `dict`
- No business logic in Phase 1 — models, infra, and plumbing only
- TDD: failing test before every implementation
- Tests run from project root: `pytest backend/tests/`
- `check_same_thread: False` required for SQLite + FastAPI
- SQLite file path: `./database/acos.db` (relative to project root)
- ChromaDB path: `./database/chroma` (relative to project root)

---

### Task 1: Python Project Setup

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `pyproject.toml` (root — tool config only, no build system)

**Interfaces:**
- Produces: `pip install -r backend/requirements.txt` and `pip install -r backend/requirements-dev.txt` succeed

- [x] **Step 1: Write requirements.txt**
- [x] **Step 2: Write requirements-dev.txt**
- [x] **Step 3: Write pyproject.toml (pytest + coverage config)**
- [x] **Step 4: Install and verify**

```bash
cd /path/to/ACOS
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pytest --version
```

- [x] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/requirements-dev.txt pyproject.toml
git commit -m "chore: add Python dependencies and pytest configuration"
```

---

### Task 2: Configuration Management

**Files:**
- Create: `backend/config.py`
- Create: `backend/tests/unit/test_config.py`

**Interfaces:**
- Produces: `from backend.config import get_settings; s = get_settings()` returns `Settings`
- `Settings.db_url` → `str` (full SQLAlchemy URL)
- `Settings.chroma_path` → `str`
- `Settings.ollama_base_url` → `str`
- `Settings.default_model` → `str`
- `Settings.embedding_model` → `str`

- [x] **Step 1–5:** Write test, fail, implement, pass, commit

---

### Task 3: Logging Infrastructure

**Files:**
- Create: `backend/logging_config.py`
- Create: `backend/tests/unit/test_logging.py`

**Interfaces:**
- Produces: `from backend.logging_config import configure_logging, get_logger`
- `configure_logging(level="INFO")` → `None`
- `get_logger("name")` → `logging.Logger`

- [x] **Step 1–5:** Write test, fail, implement, pass, commit

---

### Task 4: SQLAlchemy Models

**Files:**
- Create: `backend/models/base.py` — `Base`, `TimestampMixin`, `generate_uuid()`
- Create: `backend/models/experience.py` — `Experience`, `ExperienceBullet`
- Create: `backend/models/project.py` — `Project`
- Create: `backend/models/skill.py` — `Skill`, `SkillEvidence`, `experience_skills_table`, `project_skills_table`
- Create: `backend/models/application.py` — `Application`, `ApplicationTimeline`
- Create: `backend/models/document.py` — `Document`, `IngestionLog`
- Create: `backend/models/resume.py` — `Resume`, `ResumeTemplate`, `WritingProfile`
- Create: `backend/models/question.py` — `Question`, `Answer`
- Create: `backend/models/knowledge_graph.py` — `KnowledgeGraphNode`, `KnowledgeGraphEdge`
- Create: `backend/models/outcome.py` — `OutcomeSignal`
- Create: `backend/models/generation.py` — `GenerationLog`
- Create: `backend/models/system_config.py` — `SystemConfig`
- Create: `backend/models/__init__.py` — imports all models
- Create: `backend/tests/unit/test_models/test_experience.py`
- Create: `backend/tests/unit/test_models/test_application.py`
- Create: `backend/tests/unit/test_models/test_skill.py`

**Interfaces:**
- Produces: all model classes importable from `backend.models`
- Each model has: `id: Mapped[str]`, `created_at: Mapped[str]`

- [x] **Step 1–5:** Write tests, fail, implement, pass, commit

---

### Task 5: Database Setup

**Files:**
- Create: `backend/database.py` — `engine`, `SessionLocal`, `get_session()`, `init_db()`
- Modify: `backend/tests/conftest.py` — shared `test_session` fixture
- Create: `backend/tests/integration/test_database.py`

**Interfaces:**
- Produces: `from backend.database import get_session, init_db, engine`
- `get_session()` → generator yielding `Session`
- `init_db()` → `None` (creates all tables)

- [x] **Step 1–5:** Write test, fail, implement, pass, commit

---

### Task 6: Alembic Migrations

**Files:**
- Create: `alembic.ini` (root)
- Create: `database/migrations/env.py`
- Create: `database/migrations/script.py.mako`
- Create: `database/migrations/versions/0001_initial_schema.py` (autogenerated then committed)

- [x] **Step 1:** Write `alembic.ini`
- [x] **Step 2:** Write `database/migrations/env.py`
- [x] **Step 3:** Write `database/migrations/script.py.mako`
- [x] **Step 4:** Run autogenerate: `alembic revision --autogenerate -m "initial_schema"`
- [x] **Step 5:** Run `alembic upgrade head`
- [x] **Step 6:** Commit

---

### Task 7: Repository Layer

**Files:**
- Create: `backend/repositories/base.py` — `BaseRepository[T]`
- Create: `backend/repositories/experience.py` — `ExperienceRepository`
- Create: `backend/repositories/skill.py` — `SkillRepository`
- Create: `backend/repositories/application.py` — `ApplicationRepository`
- Create: `backend/repositories/document.py` — `DocumentRepository`
- Create: `backend/repositories/system_config.py` — `SystemConfigRepository`
- Create: `backend/repositories/__init__.py`
- Create: `backend/tests/unit/test_repositories/test_experience_repo.py`
- Create: `backend/tests/unit/test_repositories/test_skill_repo.py`

**Interfaces:**
- `BaseRepository.get(id: str) -> T | None`
- `BaseRepository.list() -> list[T]`
- `BaseRepository.create(**kwargs) -> T`
- `BaseRepository.delete(id: str) -> bool`
- `ExperienceRepository(session).get_by_company(company: str) -> list[Experience]`
- `SkillRepository(session).get_by_name(name: str) -> Skill | None`
- `ApplicationRepository(session).get_by_status(status: str) -> list[Application]`

- [x] **Step 1–5:** Write tests, fail, implement, pass, commit

---

### Task 8: ChromaDB Integration

**Files:**
- Create: `backend/rag/chroma_client.py` — `ChromaManager`
- Create: `backend/rag/collections.py` — `COLLECTION_CONFIGS`, `CollectionName` enum
- Create: `backend/rag/embedder.py` — `Embedder` (wraps Ollama)
- Create: `backend/rag/__init__.py`
- Create: `backend/tests/integration/test_chroma.py`

**Interfaces:**
- `ChromaManager(path: str)` → manager
- `ChromaManager.get_or_create_collection(name: str) -> chromadb.Collection`
- `ChromaManager.init_all_collections() -> None`
- `ChromaManager.add(collection: str, ids, documents, embeddings, metadatas) -> None`
- `ChromaManager.query(collection: str, query_embeddings, n_results, where?) -> dict`
- `ChromaManager.health_check() -> bool`
- `CollectionName` enum: `EXPERIENCES`, `PROJECTS`, `SKILLS`, `RESUMES`, `COVER_LETTERS`, `QUESTIONS`, `ANSWERS`, `JOB_DESCRIPTIONS`, `GITHUB`, `CLAUDE_EXPORTS`

- [x] **Step 1–5:** Write tests, fail, implement, pass, commit

---

### Task 9: Ollama Integration

**Files:**
- Create: `backend/services/ollama_client.py` — `OllamaClient`
- Create: `backend/services/__init__.py`
- Create: `backend/tests/integration/test_ollama.py`

**Interfaces:**
- `OllamaClient(base_url: str, timeout: int)`
- `OllamaClient.is_available() -> bool`
- `OllamaClient.generate(model: str, prompt: str, temperature: float, max_tokens: int | None) -> str`
- `OllamaClient.embed(model: str, text: str) -> list[float]`
- `OllamaClient.list_models() -> list[str]`

- [x] **Step 1–5:** Write tests (with respx mocks), fail, implement, pass, commit

---

### Task 10: FastAPI Application

**Files:**
- Create: `backend/main.py` — app factory with lifespan
- Create: `backend/api/v1/routes/health.py`
- Create: `backend/api/__init__.py`, `backend/api/v1/__init__.py`, `backend/api/v1/routes/__init__.py`
- Create: `backend/tests/integration/test_health.py`

**Interfaces:**
- `GET /api/v1/health` → `{"status": "ok", "db": "connected", "version": "0.1.0"}`
- `GET /api/v1/health/ollama` → `{"available": bool, "models": list[str]}`

- [x] **Step 1–5:** Write test, fail, implement, pass, commit

---

### Task 11: Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`, `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/vite-env.d.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src-tauri/Cargo.toml`
- Create: `frontend/src-tauri/build.rs`
- Create: `frontend/src-tauri/tauri.conf.json`
- Create: `frontend/src-tauri/src/lib.rs`
- Create: `frontend/src-tauri/src/main.rs`

- [x] **Step 1–5:** Write files, run `tsc --noEmit`, commit

---

### Task 12: Quality Gates

- [ ] `pytest backend/tests/ --cov=backend --cov-report=term-missing` ≥ 90%
- [ ] `/code-review` skill
- [ ] `/security-review` skill (file I/O paths in Document model)
- [ ] Commit

---

## Self-Review Checklist

| Requirement | Task |
|-------------|------|
| Configuration management | Task 2 |
| Logging infrastructure | Task 3 |
| SQLAlchemy models (all 18 tables) | Task 4 |
| SQLite setup | Task 5 |
| Alembic migrations | Task 6 |
| Repository layer | Task 7 |
| ChromaDB integration | Task 8 |
| Ollama integration | Task 9 |
| FastAPI skeleton + health | Task 10 |
| Frontend scaffold | Task 11 |
| Tests ≥ 90% coverage | Task 12 |
| No business logic | ✓ confirmed |
