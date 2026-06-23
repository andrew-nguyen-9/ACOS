# Phase 12.12 — Resume Strategy Intelligence Layer

**Track:** Flywheel · **Depends on:** 12.10, 12.11 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned

## 1. Context

Signals (12.10) + skill ROI (12.11) feed strategy: best-practice resume templates, industry-specific
structures, and adaptive ATS strategies — always **personalized to the tenant**, grounded in their
evidence (no hallucinated "best practices"). This is the recommendation layer the user sees.

## 2. Goals

- **Best-practice templates:** structural templates derived from what performed well (locally now; the
  global library arrives via 12.15).
- **Industry-specific structures:** section ordering / emphasis recommendations keyed by target industry.
- **Adaptive ATS strategy:** keyword-density + skill-ordering guidance per job description, using ROI ranks.
- **Per-tenant personalization:** all recommendations cite the tenant's own evidence + confidence level.

## 3. Non-goals (YAGNI)

- No autogeneration of a full resume here — this advises the existing resume engine; it doesn't replace it.
- No global/cross-tenant templates yet (12.15 supplies anonymized patterns; this layer consumes them later).
- No new export formats.

## 4. Acceptance criteria

- [ ] `strategy.recommend(tenant_id, target_jd)` returns structure + ATS guidance with confidence + evidence links.
- [ ] Recommendations degrade gracefully with little data (clearly marked `weak_inference`, never fabricated).
- [ ] Industry structures keyed by a defined industry taxonomy; unknown industry → generic + flagged.
- [ ] Output integrates with the resume engine inputs (no schema mismatch).
- [ ] ≥90% coverage; existing tests green.

## 5. Design

- `backend/services/flywheel/strategy.py`: composes ROI ranks + signal rollups + JD analysis into a
  `StrategyRecommendation` dataclass (structure, emphasis, keyword targets, confidence, evidence).
- Read route `GET /flywheel/strategy`. Consumed by the resume/ATS UI.
- `skill-creator` may extend the industry/skill taxonomy that keys recommendations.

## 6. File-level plan

```
NEW  backend/services/flywheel/strategy.py
EDIT backend/api/v1/routes/flywheel.py        (strategy endpoint)
EDIT backend/services/resume/*                (accept strategy hints as optional input)
NEW  backend/tests/unit/test_strategy_intelligence.py
```

## 7. Test plan (TDD)

- `test_strategy_intelligence.py`: rich tenant data → confident structured recs with evidence; sparse data → generic + weak_inference; unknown industry handled.

## 8. Plugin orchestration checklist

- [ ] `skill-creator` — industry/skill ontology expansion.
- [ ] `serena` — cross-domain reasoning over signals → strategy (per brief plugin requirements).
- [ ] `ralph-skills` — ROI inputs.
- [ ] `superpowers:test-driven-development`; `explanatory-output-style` for the rationale.

## 9. Perf budget impact

Read-side; cached per (tenant, JD-hash). No request-path regression.

## 10. Definition of Done

Personalized structure + ATS strategy with confidence + evidence, resume-engine integration, taxonomy-keyed, tested ≥90%, PR.
