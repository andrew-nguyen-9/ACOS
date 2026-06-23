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

## Hot-path pragmas & durability

`backend/database.py` applies these on every connection (`_apply_pragmas`, Phase 12.1):

| Pragma | Value | Why |
|--------|-------|-----|
| `journal_mode` | `WAL` | Concurrent readers + writer; persistent in the file header. |
| `synchronous` | `NORMAL` (1) | Fewer fsyncs on the write path. |
| `mmap_size` | `268435456` (256 MiB) | Memory-mapped reads cut syscall overhead. |
| `foreign_keys` | `ON` | Enforce referential integrity (per-connection default is OFF). |

**Durability — `NORMAL` is safe under WAL.** In rollback-journal mode `NORMAL` risks
corruption on a power loss, but under WAL it does not: the database stays consistent and the
only residual risk is losing the *last* committed transaction(s) on an OS crash or power cut
(an fsync happens at WAL checkpoints, not on every commit). For a local single-user desktop
app that trade is acceptable. Use `FULL` only if last-transaction loss is unacceptable.
Of these, only `journal_mode` persists in the file; the rest reset to defaults on each new
connection, so they are re-applied per connect.

## Migrations (Alembic)

Configured in [`../alembic.ini`](../alembic.ini) (`script_location = database/migrations`).

```bash
alembic upgrade head                          # apply all migrations
alembic revision --autogenerate -m "message"  # create a new migration
alembic downgrade -1                          # roll back one step
```

ORM models in [`../backend/models/`](../backend/models/) are the source of truth for the
schema; migrations make the database match them.

## Migration rules

**Every migration must define a working `downgrade()`.** This is enforced by
`backend/tests/integration/test_migration_roundtrip.py`, which runs the full
revision chain `upgrade head → downgrade base → upgrade head` on a temp DB. A
migration that cannot be cleanly reversed will fail that test.

## Resetting local data

`acos.db` and `chroma/` are regenerated from migrations + ingestion, so deleting them
gives a clean slate:

```bash
rm -f database/acos.db && rm -rf database/chroma
alembic upgrade head
python scripts/ingestion/ingest_static_files.py
```
