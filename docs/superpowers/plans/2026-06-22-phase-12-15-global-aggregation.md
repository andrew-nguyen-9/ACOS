# Phase 12.15 — Privacy-Preserving Global Pattern + ROI Aggregation

**Track:** Multi-tenant · **Depends on:** 12.11, 12.14 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Produces ADR-009**

> **Read the roadmap's "Privacy boundary" section first — it is binding.** No raw content, no PII, no
> per-tenant identifiers cross the boundary. k-anonymity (k ≥ 5) before any pattern is emitted.
> Cross-device sync is OUT OF SCOPE here (local multi-tenant only; future sync is opt-in + a new ADR).

## 1. Context

With tenants isolated (12.14) and per-tenant skill ROI (12.11), the brief asks for *cross-user*
intelligence: resume structures that consistently succeed, ATS keyword patterns by industry, effective
cover-letter structures, high-performing skill clusters — **as abstractions only**. This segment builds
the anonymized aggregation layer over local tenants and the global (cross-tenant) ROI/pattern views.

## 2. Goals

- **Cross-tenant pattern extractor:** mine *structural/statistical* patterns (section ordering, keyword
  density bands, skill clusters) across tenants — never raw text.
- **Global skill-ROI model:** aggregate per-tenant ROI (12.11) into "highest ROI skills per industry"
  and "fastest interview-improvement skills" globally.
- **Anonymization guarantees:** an emission gate enforcing k-anonymity (k ≥ 5 contributing tenants),
  no field that could re-identify a tenant, and aggregation-only outputs.
- **Feed back, personalized:** the global library is consumed by 12.12 strategy as *suggestions*, always
  re-personalized per tenant — global never overrides local evidence.

## 3. Non-goals (YAGNI — strict)

- **No network transmission.** Operates on local tenants only; nothing leaves the machine (CLAUDE.md local-only).
- No raw content, embeddings, or per-tenant rows in any global artifact.
- No global *prompt* auto-promotion — global signals can *propose* (12.13) but promotion stays local + approval-gated.
- No differential-privacy noise engine unless k-anonymity proves insufficient (`# ponytail: k-anonymity gate first; add DP noise only if a re-id test defeats it`).

## 4. Acceptance criteria

- [ ] Aggregation runs over ≥2 local tenants and emits **only** abstracted patterns + counts.
- [ ] Emission gate **drops** any pattern backed by < k (=5) tenants (test asserts suppression).
- [ ] A re-identification test confirms no global artifact contains raw text, embeddings, or tenant ids.
- [ ] Global ROI view returns industry-keyed rankings with aggregate confidence (no per-tenant attribution).
- [ ] 12.12 strategy can consume global patterns as suggestions, re-personalized + confidence-tagged.
- [ ] ADR-009 (privacy-preserving aggregation; k-anonymity; no-network) written.
- [ ] ≥90% coverage; existing tests green.

## 5. Design

- `backend/services/flywheel/global_patterns.py`: reads per-tenant rollups/ROI (never rows), computes
  abstractions, passes them through `anonymization.gate()` before persisting to a `global_patterns` store.
- `backend/services/flywheel/anonymization.py`: k-anonymity threshold + field allowlist (only abstract
  fields may be emitted) + a re-id self-check used by tests.
- Global store is a separate, content-free table; 12.12 reads it as optional input.

## 6. File-level plan

```
NEW  backend/services/flywheel/global_patterns.py
NEW  backend/services/flywheel/anonymization.py
NEW  backend/models/global_pattern.py                 (content-free aggregate store; + register)
NEW  database/migrations/versions/<rev>_phase12_global_patterns.py
EDIT backend/services/flywheel/strategy.py (12.12)    (consume global suggestions, re-personalized)
EDIT backend/api/v1/routes/flywheel.py                (global ROI read endpoint)
NEW  docs/adr/ADR-009-privacy-preserving-aggregation.md
NEW  backend/tests/unit/test_anonymization_gate.py
NEW  backend/tests/integration/test_global_aggregation.py
NEW  backend/tests/unit/test_no_reidentification.py
```

## 7. Test plan (TDD)

- `test_anonymization_gate.py`: patterns with < k tenants suppressed; disallowed fields rejected.
- `test_no_reidentification.py`: scan every global artifact → no raw text / embeddings / tenant id.
- `test_global_aggregation.py`: multi-tenant fixture → correct industry rankings, aggregate-only, k-respected.

## 8. Plugin orchestration checklist

- [ ] `ralph-loop` — global optimization layer (per brief).
- [ ] `ralph-skills` — global skill-ROI modeling.
- [ ] `serena` — cross-domain pattern reasoning.
- [ ] `explanatory-output-style` — global insights reporting (aggregate, no attribution).
- [ ] `superpowers:test-driven-development`; `security-review` — privacy boundary is the deliverable.

## 9. Perf budget impact

Aggregation is a batch/off-hot-path job; results cached. Read endpoints serve cached aggregates. No request-path regression.

## 10. Definition of Done

Cross-tenant pattern extractor + global ROI, k-anonymity emission gate, no-reidentification test green,
global suggestions feed 12.12 re-personalized, ADR-009, no network, tested ≥90%, security review passed, PR.
