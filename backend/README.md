# Backend

FastAPI application for ACOS. Python 3.11+, SQLAlchemy 2.0, Pydantic v2.

> Full architecture: [`../docs/ARCHITECTURE_OVERVIEW.md`](../docs/ARCHITECTURE_OVERVIEW.md) ·
> Schema: [`../docs/04_DATABASE_SCHEMA.md`](../docs/04_DATABASE_SCHEMA.md)

## Layering (strict)

```
api/v1/routes → services → repositories → models → SQLite
                   ├→ rag/        → ChromaDB
                   └→ ollama_client → Ollama
```

- **`api/v1/routes/`** — HTTP endpoints only. No business logic; they call services.
- **`services/`** — business logic, one package per domain (`resume/`, `cover_letter/`,
  `ats/`, `copilot/`, `questions/`, `knowledge_graph/`, `learning/`, `optimization/`, `rag/`).
- **`repositories/`** — the *only* layer that touches the database. One repo per model.
- **`models/`** — SQLAlchemy ORM models; the schema expressed in code.
- **`rag/`** — ChromaDB client, collections, embedder, retriever, reranker.
- **`ingestion/`** — file → structured entities; `parsers/` handles PDF/DOCX/MD/TXT.
- **`prompts/`** — versioned YAML prompt templates, loaded by `services/prompt_loader.py`.

## Entry points

| File | Role |
|------|------|
| `main.py` | App factory — wires routers, middleware, lifespan. |
| `server_entry.py` | PyInstaller entry; runs uvicorn on `127.0.0.1:8000`. |
| `config.py` | Pydantic settings (Ollama URL, model names, DB/Chroma paths). |

## Run & test

```bash
uvicorn backend.main:app --reload --port 8000   # API + Swagger at /docs
pytest                                           # unit + integration (coverage gate ≥90%)
pyright                                          # type checking
```

## Conventions

- **TDD**: tests are written before implementation (see [`../CLAUDE.md`](../CLAUDE.md)).
- `tests/` mirrors the source layout: `unit/`, `integration/`, `benchmark/`.
- Every generated career statement carries a confidence level
  ([ADR-006](../docs/adr/ADR-006-evidence-confidence-system.md)).
- All file I/O and user input must be security-reviewed; never exec parsed content.
