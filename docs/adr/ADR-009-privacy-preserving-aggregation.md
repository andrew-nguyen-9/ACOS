# ADR-009: Privacy-Preserving Cross-Tenant Aggregation — k-Anonymity, Content-Free, No Network

**Status:** Accepted
**Date:** 2026-06-22
**Deciders:** Andrew Nguyen
**Phase:** 12.15

---

## Context

With tenants isolated (12.14, ADR-008) and per-tenant skill ROI (12.11), Phase 12 asks
for *cross-tenant* intelligence: which skills/structures succeed across local profiles.
This crosses the privacy boundary the roadmap draws: one tenant's data must never be
re-identifiable from a cross-tenant artifact. The aggregation is a privacy boundary, so
it gets an explicit, enforced contract rather than per-call discipline.

---

## Decision

### 1. Read aggregates, never rows

The aggregator reads each tenant's **ROI / rollups** (12.11 `rank_skills`, 12.10
`rollup`) — never raw signal rows, resume text, or embeddings. ROI is already an
effect-size abstraction; aggregating abstractions cannot leak content that the
abstraction didn't already contain.

### 2. A k-anonymity emission gate is the deliverable

Every candidate global pattern passes through `anonymization.gate()` before it can be
persisted or returned. The gate enforces two hard rules:

- **k-anonymity (k = 5):** a pattern backed by fewer than 5 contributing tenants is
  **dropped**, not emitted. A pattern that only ≤4 tenants exhibit could finger those
  tenants; suppression is mandatory, not advisory.
- **Field allowlist:** only an explicit set of abstract fields may appear on a global
  pattern (`pattern_type`, `industry`, `key`, `value`, `metric`, `tenant_count`,
  `confidence`). Any other field — especially anything resembling a tenant id, raw text,
  or an embedding — raises `ReidentificationError`. Default-closed: a new field is
  rejected until explicitly allowlisted.

### 3. The global store is content-free

`global_patterns` holds only abstract fields: a pattern type, an industry key, an
abstract label (e.g. a skill name — shared vocabulary, not user content), an aggregate
numeric value, a contributing-tenant **count** (not ids), and a confidence level. It
carries **no `tenant_id`** (it is cross-tenant by definition, so it is NOT a
`TenantScopedMixin` table), no raw text, and no embeddings. A re-identification test
scans every emitted artifact to prove this.

### 4. No network

Aggregation runs over **local** tenants only; nothing leaves the machine (CLAUDE.md
local-only). There is no transmission, sync, or upload. Cross-device sync, if ever
built, is a separate opt-in feature with its own ADR.

### 5. Global never overrides local

12.12 strategy consumes global patterns as **suggestions only**, re-personalized against
the tenant's own evidence and confidence-tagged. A global pattern can *propose* a prompt
change (12.13) but promotion stays local + approval-gated — global signals never
auto-mutate a tenant's prompts.

### 6. k-anonymity first; DP noise only if defeated

We start with k-anonymity + the field allowlist. Differential-privacy noise is **not**
added unless a re-identification test defeats the gate — it is complexity we add only
against a demonstrated attack (`# ponytail: k-anonymity gate first`).

---

## Consequences

**Positive**
- A cross-tenant artifact cannot, by construction, carry content or per-tenant ids.
- Small-cohort patterns are suppressed automatically.
- The boundary is one gate, testable in isolation (suppression + allowlist + re-id scan).

**Negative**
- With < 5 local profiles, the gate suppresses *everything* — global intelligence only
  appears once enough profiles exist. This is the correct privacy tradeoff, not a bug.
- The field allowlist must be updated deliberately when a genuinely new abstract field
  is needed (default-closed friction).

**Mitigations**
- The gate is a pure function with a re-id self-check the tests reuse.
- `tenant_count` (a count, never ids) gives downstream consumers a confidence signal
  without exposing membership.
