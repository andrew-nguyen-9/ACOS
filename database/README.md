# Database

Persistence for ACOS: a SQLite relational database plus a ChromaDB vector store. Both are
**local runtime data** and are git-ignored — only migrations, seed data, and structure are
versioned.

> Schema reference: [`../docs/04_DATABASE_SCHEMA.md`](../docs/04_DATABASE_SCHEMA.md) ·
> Decisions: [ADR-002 (SQLite)](../docs/adr/ADR-002-sqlite-primary-database.md),
> [ADR-003 (ChromaDB)](../docs/adr/ADR-003-chromadb-vector-store.md)

## Layout

| Path | Versioned? | Purpose |
|------|-----------|---------|
| `migrations/` | ✅ | Alembic migrations — `env.py`, `script.py.mako`, `versions/`. |
| `seed/` | ✅ | Seed data loaded on first run. |
| `backups/` | dir only | Destination for DB backups (contents ignored). |
| `acos.db` | ❌ ignored | The SQLite database (runtime). |
| `chroma/` | ❌ ignored | ChromaDB persistent store (runtime). |

## Migrations (Alembic)

Configured in [`../alembic.ini`](../alembic.ini) (`script_location = database/migrations`).

```bash
alembic upgrade head                          # apply all migrations
alembic revision --autogenerate -m "message"  # create a new migration
alembic downgrade -1                          # roll back one step
```

ORM models in [`../backend/models/`](../backend/models/) are the source of truth for the
schema; migrations make the database match them.

## Resetting local data

`acos.db` and `chroma/` are regenerated from migrations + ingestion, so deleting them
gives a clean slate:

```bash
rm -f database/acos.db && rm -rf database/chroma
alembic upgrade head
python scripts/ingestion/ingest_static_files.py
```
