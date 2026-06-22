# ADR-008: Multi-Tenant Isolation — One Database, Enforced `tenant_id`, Local-Profile Model

**Status:** Accepted
**Date:** 2026-06-22
**Deciders:** Andrew Nguyen
**Phase:** 12.14

---

## Context

ACOS began single-user: no tenant or user model existed. Phase 12 requires per-tenant
isolation so the flywheel (12.10–12.13) and global aggregation (12.15) can reason about
multiple local career profiles without leaking one profile's data into another.

The data spans four stores that all must be isolated together:

- **SQLite** — career content (experiences, projects, skills, applications, resumes,
  Q&A, documents) + derived rows (generation logs, metrics, memory, knowledge graph,
  outcome signals, and the 12.10 `signals` table).
- **ChromaDB** — vector embeddings of that content.
- **Knowledge graph** — nodes/edges (stored in SQLite).
- **Outcome tracking** — outcome signals + the flywheel signal table.

A leak in any one store defeats the boundary, so isolation is a single decision applied
across all of them.

---

## Decision

### 1. One database, enforced `tenant_id` — not physical per-tenant files

A single SQLite file and a single Chroma path. Every tenant-owned row carries a
`tenant_id` FK to a `tenants` table; every Chroma record carries `tenant_id` in its
metadata. We reject per-tenant database files: on a single-user machine they add
file-handle and migration complexity with no security benefit over an enforced column.

### 2. Local-profile model — no authentication

A "tenant" is a **local profile**, not a network identity. There is no login, no
session token, no multi-device sync. The threat model is "don't let profile A's content
bleed into profile B's generations or aggregates," not "defend against a remote
attacker." Real authentication is a separate future phase if ever needed.

`# ponytail: local profiles now; real authn is a separate phase if ever needed.`

### 3. Tenant resolved once at the session boundary + a central repository guard

The tenant is resolved **once per request** at the session-dependency boundary
(`get_session` / `get_async_session`) and stored on `session.info["tenant_id"]`. The
central guard lives in `BaseRepository`:

- **Read** (`get`/`list`/`count`): auto-filters to the current tenant. A tenant-scoped
  model queried with **no tenant set raises `TenantScopeError`** — a missing filter is a
  hard error, never a silent full-table read.
- **Write** (`create`): auto-injects the current `tenant_id` when the caller didn't
  supply one. Same hard error if no tenant is set.
- **Cross-tenant `get`**: a row owned by another tenant resolves to `None` (not the row).

This makes isolation a property of the repository layer, not per-query discipline —
adding a new repository call cannot forget to scope, because the base enforces it.

**Belt-and-suspenders:** tenant-scoped routers *also* declare an explicit
`Depends(get_tenant_context)` (router-level), so the request-scoped `TenantContext` is a
visible part of each route's contract as well as enforced at the session layer.

### 4. What is tenant-owned vs shared

**Tenant-owned (carry `tenant_id`):** experiences, projects, skills, applications,
resumes, writing_profiles, questions, answers, documents, generation_logs,
knowledge_graph_nodes, knowledge_graph_edges, outcome_signals, metrics, memory, signals.

**Shared (no `tenant_id`):** system_config, resume_templates, prompt_versions,
ab_experiments, ab_variants, optimization_proposals, optimization_logs, maintenance_*,
schema_migrations. These are application code / base templates / operational rows — the
roadmap's "share only code + base prompt templates." Child tables
(experience_bullets, skill_evidence, application_timeline, ingestion_logs) inherit
isolation through their parent FK and are reached only via a scoped parent.

### 5. Migration: nullable → backfill → NOT NULL in one revision

A single Alembic revision creates `tenants`, inserts a `default` tenant, then for each
owned table: adds `tenant_id` nullable, backfills every existing row to `default`, and
rebuilds the table with `tenant_id NOT NULL` + FK (SQLite needs `batch_alter_table`).
Existing single-user data is losslessly re-homed into the `default` tenant. The app
boots schema via `create_all` (not Alembic at runtime), so the SQLAlchemy models carry
`tenant_id` too (create_all parity) — the migration is for already-populated databases.

---

## Consequences

**Positive**
- A new query physically cannot run unscoped — the guard raises.
- One migration, one DB, one Chroma path — operationally simple on a local machine.
- Existing tests stay green: create auto-injects and reads auto-filter to the same
  `default` tenant, so single-tenant flows are unchanged.
- 12.15 can enumerate tenants and read per-tenant rollups without ever touching rows.

**Negative**
- Every tenant-scoped query carries a `tenant_id` predicate (mitigated by an index).
- The guard couples the repository base to the tenancy module.
- A bypass for legitimate cross-tenant work (12.15 aggregation) must read **rollups**,
  not rows — it never bypasses the row guard.

**Mitigations**
- `tenant_id` is indexed on every owned table.
- `session.info` is request-scoped (one session per request), so there is no global
  mutable tenant state to leak across requests.

## Chroma read-filter status

`ChromaManager` composes a tenant `where` (AND-ed with the 12.6 `doc_type` filter) and
the indexer **tags every vector write** with the active tenant. SQLite — the authoritative
store — is fully guarded. Live RAG **read**-filtering is intentionally not yet wired into
`RAGRetriever`'s call sites: filtering reads by `tenant_id` before existing vectors are
re-tagged would return nothing. Enabling it is a two-step operational change (reindex to
backfill Chroma metadata, then pass the tenant through `EvidenceSelector` / `RAGService`),
landed when multi-profile RAG is actually exercised. Under today's single-profile reality
every vector is the `default` tenant, so there is no isolation gap in practice.

## Forward-looking: `X-Tenant-Id` and authentication

`X-Tenant-Id` is an **unauthenticated** profile selector — safe under the local-only model
(no network listener for other principals). If ACOS is ever exposed beyond localhost or
made multi-user, this header becomes a direct cross-tenant IDOR and **must** be gated
behind the future authentication layer.

---

## Alternatives considered

- **Physical per-tenant DB files** — rejected (§1): complexity without benefit on a
  single-user machine.
- **Per-query `.filter(tenant_id=...)` discipline** — rejected: the exact failure mode
  the guard exists to kill is a forgotten filter.
- **Per-route dependency only (no session guard)** — rejected: a new route can forget the
  dependency. We keep the dependency for readability but enforce at the session layer.
