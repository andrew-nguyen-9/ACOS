# Phase 12.11 — Skill ROI Engine

**Track:** Flywheel · **Depends on:** 12.10 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned

## 1. Context

With local signals (12.10) flowing, compute the relationship between skills and outcomes: which skills
correlate with interview lift, ATS-score impact, and (where data exists) offer probability. Output a
ranked, explainable "highest-ROI skills" view, scoped per tenant (global version is 12.15).

## 2. Goals

- **Correlations:** skill → interview-lift, skill → ATS-score delta, skill → offer-probability.
- **ROI ranking:** "highest ROI skills" and "fastest interview-improvement skills" for the tenant.
- **Confidence-aware:** every ROI figure carries a sample size + confidence level (verified /
  strong_inference / weak_inference per ADR-006); low-n figures flagged, never asserted.

## 3. Non-goals (YAGNI)

- No heavy ML — correlation + simple regression/effect-size over the tenant's signals
  (`# ponytail: effect-size + n is honest and explainable; upgrade to a model only with enough data`).
- No cross-tenant aggregation (12.15).
- No skill *ontology* creation here — consumes existing skills + the taxonomy 12.12 may extend.

## 4. Acceptance criteria

- [ ] `roi.rank_skills(tenant_id, metric)` returns skills ranked by ROI with sample size + confidence.
- [ ] Low-sample skills are tagged `weak_inference` and excluded from "recommended" output.
- [ ] ROI for a skill is explainable: lists the contributing signals/outcomes.
- [ ] Deterministic on a fixed signal set (golden test).
- [ ] ≥90% coverage; existing tests green.

## 5. Design

- `backend/services/flywheel/skill_roi.py`: pull tenant signals, group by skill, compute effect size +
  n + confidence, rank. Pure functions over the rollups from 12.10.
- Expose via a read-only route (e.g. `GET /flywheel/skills/roi`) for the UI.

## 6. File-level plan

```
NEW  backend/services/flywheel/skill_roi.py
NEW  backend/api/v1/routes/flywheel.py        (read-only ROI endpoints)
EDIT backend/services/flywheel/feedback.py     (helpers if needed)
NEW  backend/tests/unit/test_skill_roi.py
```

## 7. Test plan (TDD)

- `test_skill_roi.py`: known signal fixture → expected ranking + confidence; low-n skill flagged weak; explanation lists sources.

## 8. Plugin orchestration checklist

- [ ] `ralph-skills` — ROI modeling.
- [ ] `skill-creator` — only if the skill taxonomy needs nodes to attach ROI to.
- [ ] `superpowers:test-driven-development`.
- [ ] `explanatory-output-style` — ROI rationale is user-facing.

## 9. Perf budget impact

Read-side computation over cached rollups; cache results. No request-path regression.

## 10. Definition of Done

ROI correlations + ranking + confidence + explainability, read endpoint, golden test, ≥90% coverage, PR.
