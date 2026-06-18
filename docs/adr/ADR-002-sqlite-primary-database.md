# ADR-002: SQLite as Primary Relational Database

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

The system needs a relational database for structured career data (experiences, applications,
skills, documents). Options include SQLite, PostgreSQL (local), DuckDB, and others.

---

## Decision

Use SQLite as the primary relational database, accessed via SQLAlchemy ORM.

---

## Consequences

**Positive:**
- Zero-configuration; no database server to manage
- Single file database — trivially portable and backupable
- SQLAlchemy abstracts the dialect; migration to PostgreSQL is possible later
- Sufficient for single-user local workload
- Built into Python stdlib (sqlite3)
- Alembic migration support identical to PostgreSQL

**Negative:**
- No concurrent write support (single-writer)
- No full-text search (use ChromaDB instead)
- Limited to ~1TB file size (not relevant for this use case)

**Mitigations:**
- Single-user application; concurrent writes are not a use case
- Full-text and semantic search handled by ChromaDB
- SQLAlchemy ORM means switching to PostgreSQL later requires only connection string change

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| PostgreSQL (local) | Requires running a separate server process; overkill for single-user |
| DuckDB | Excellent for analytics but less mature ORM ecosystem |
| TinyDB | No SQL, no migrations, no SQLAlchemy |
| MongoDB (local) | Document DB is wrong shape for relational career data |
