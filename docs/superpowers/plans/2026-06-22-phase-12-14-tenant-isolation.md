# Phase 12.14 — Tenant Isolation Framework

**Track:** Multi-tenant · **Depends on:** 12.2 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Produces ADR-008**

> Foundational and broad. Land **before** persisting flywheel data (12.10) so everything is
> tenant-scoped from day one. Read the "Privacy boundary" section of the roadmap first.

## 1. Context

ACOS is single-user: no tenant/user model exists (verified — no `tenant`/`user_id` in `backend/models/`).
The Phase 12 brief requires per-tenant isolation: separate DB namespace, vector collections, knowledge
graph, and outcome tracking, sharing only code + base prompt templates + (later, 12.15) an anonymized
pattern layer.

## 2. Goals

- **Tenant model + context:** a `tenants` table; a request-scoped `TenantContext` (resolved once,
  threaded through services) so no query runs without a tenant.
- **SQLite namespacing:** `tenant_id` FK on every tenant-owned table + migration; repositories enforce
  the filter centrally (single choke point, not per-query discipline).
- **Vector isolation:** `tenant_id` in Chroma metadata; every write/query carries a `where` tenant filter
  (composed with the `doc_type` filter from 12.6).
- **Knowledge graph + outcomes:** scope `knowledge_graph`, `outcome`, `metric`, `memory`, and new `signals`
  (12.10) by tenant.
- **Default tenant migration:** existing single-user data migrates into a `default` tenant (lossless).

## 3. Non-goals (YAGNI)

- No auth / login / multi-device — a "tenant" is a local profile, not a network identity
  (`# ponytail: local profiles now; real authn is a separate phase if ever needed`).
- No cross-tenant reads of any kind (12.15 only sees anonymized aggregates, never rows).
- No physical per-tenant databases — one DB, enforced `tenant_id` (simpler, single-user-machine reality).

## 4. Acceptance criteria

- [ ] `tenants` table; `TenantContext` dependency required by every tenant-scoped route.
- [ ] `tenant_id` FK on all tenant-owned tables; migration backfills existing rows to `default`.
- [ ] A **central guard** makes a missing tenant filter a hard error (test: a query without tenant raises, not leaks).
- [ ] Chroma reads/writes always carry the tenant `where` filter; a cross-tenant query returns nothing (test).
- [ ] Cross-tenant isolation test: tenant A cannot read tenant B's rows or vectors via any route.
- [ ] ADR-008 (tenant isolation: one-DB + enforced tenant_id, local-profile model) written.
- [ ] Full suite green (tests updated to pass a tenant); ≥90% coverage on the isolation layer.

## 5. Design

- `backend/models/tenant.py` + `tenant_id` columns via one migration (`# ponytail: nullable→backfill→NOT NULL in one revision`).
- `backend/services/tenancy.py`: `TenantContext`, `current_tenant()` dependency, `scoped(query, tenant)` helper.
- Repositories: base method applies the tenant filter; bypass requires an explicit, audited admin path (none in prod).
- Chroma: `chroma_client` write/query signatures take `tenant_id`; merged into the metadata `where`.
- Migration re-homes existing SQLite rows + Chroma metadata to `default`.

## 6. File-level plan

```
NEW  backend/models/tenant.py                         (+ register)
NEW  backend/services/tenancy.py                       (TenantContext + guard)
EDIT backend/models/* (tenant_id FK on owned tables)
EDIT backend/repositories/* (central tenant filter)
EDIT backend/rag/chroma_client.py / indexer / retriever (tenant in metadata + where)
EDIT backend/api/v1/routes/* (require TenantContext)
NEW  database/migrations/versions/<rev>_phase12_tenants.py   (table + columns + backfill default)
NEW  docs/adr/ADR-008-multi-tenant-isolation.md
NEW  backend/tests/integration/test_tenant_isolation.py
NEW  backend/tests/unit/test_tenancy_guard.py
```

## 7. Test plan (TDD)

- `test_tenancy_guard.py`: query without tenant → raises; with tenant → scoped.
- `test_tenant_isolation.py`: seed tenants A & B; assert no route/repo/Chroma path leaks across; default-tenant backfill correct.

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLAlchemy multi-tenant patterns, Chroma metadata filtering.
- [ ] `serena` — reason about isolation across the SQLite + Chroma + KG seams.
- [ ] `superpowers:test-driven-development` + `requesting-code-review` (security-critical, broad).
- [ ] `security-guidance` / `security-review` — isolation is a security boundary; review for leak paths.

## 9. Perf budget impact

Adds an indexed `tenant_id` filter to queries (negligible with an index). One-time migration cost. Bench to confirm no request-path regression.

## 10. Definition of Done

Tenant model + enforced isolation across SQLite/Chroma/KG/outcomes, default-tenant migration, leak
tests green, ADR-008, ≥90% coverage, security review passed, PR.
