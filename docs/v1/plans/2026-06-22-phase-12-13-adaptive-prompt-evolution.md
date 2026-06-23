# Phase 12.13 — Adaptive Prompt Evolution

**Track:** Flywheel · **Depends on:** 12.10, 12.11; **builds on** Phase 11.2 (prompt locking/versioning)
**Branch:** `feat/phase-12-velocity-flywheel-multitenant` · **Status:** Planned

> Touches generation quality. Hard rule (from Phase 11): all prompt changes stay **versioned,
> reversible, and explainable**. No autonomous, unreviewable prompt mutation in production.

## 1. Context

Phase 11.2 locked prompts to versions with observability. Phase 12 lets prompts **evolve** based on
success signals (per-user from 12.10, and later global from 12.15) — but evolution must be a
*proposal* that is versioned and reversible, not a silent live mutation.

## 2. Goals

- **Signal-driven proposals:** when signals show a prompt variant underperforms, generate a candidate
  revision as a new **version** (never overwrite the active one).
- **A/B harness:** reuse `services/optimization/` (Phase 8/11) to trial a candidate vs incumbent on a
  guardrailed slice; promote only on a clear, measured win.
- **Reversible + explainable:** every promotion records why (which signals), and a one-call rollback.
- **Approval-gated:** promotion of a new active prompt requires explicit user approval (no autonomous prod change).

## 3. Non-goals (YAGNI)

- No reinforcement-learning prompt search — bounded, human-approved candidate generation only.
- No global prompt sharing here (12.15, anonymized + opt-in).
- No change to the prompt-loading/locking mechanism from 11.2 — extend, don't replace.

## 4. Acceptance criteria

- [ ] A candidate prompt is created as a new version with a rationale linked to signals; incumbent untouched.
- [ ] A/B trial runs through the existing optimization guardrails; results recorded.
- [ ] Promotion requires explicit approval; a rollback restores the prior active version in one call.
- [ ] Full audit trail: who/what/why for every version transition (extends 11.2 observability).
- [ ] ≥90% coverage; existing prompt tests green.

## 5. Design

- `backend/services/flywheel/prompt_evolution.py`: `propose(prompt_id, signals)`, `trial(candidate)`,
  `promote(version, approved_by)`, `rollback(prompt_id)`.
- Versions stored via the existing prompt-version table/loader (11.2); evolution only adds rows + transitions.
- A/B via `services/optimization/` evolver + guardrails (already exist).

## 6. File-level plan

```
NEW  backend/services/flywheel/prompt_evolution.py
EDIT backend/services/prompt_loader.py / prompt-version store   (candidate versions + active pointer)
EDIT backend/services/optimization/*                            (wire prompt A/B)
EDIT backend/api/v1/routes/ (optimization or flywheel)          (propose/trial/promote/rollback, approval-gated)
NEW  backend/tests/unit/test_prompt_evolution.py
NEW  backend/tests/integration/test_prompt_ab_promotion.py
```

## 7. Test plan (TDD)

- `test_prompt_evolution.py`: propose → new version, incumbent unchanged; rollback restores prior; rationale links signals.
- `test_prompt_ab_promotion.py`: trial → result recorded; promote blocked without approval; promote with approval flips active pointer + audit row.

## 8. Plugin orchestration checklist

- [ ] `ralph-loop` — optimization-loop layer for candidate trialing (per brief plugin requirements).
- [ ] `superpowers:test-driven-development` + `requesting-code-review` (quality-affecting).
- [ ] `explanatory-output-style` — promotion rationale is user-facing.

## 9. Perf budget impact

Trials run off the hot path / opt-in. Active-prompt resolution stays O(1) (pointer lookup); no per-request regression.

## 10. Definition of Done

Versioned reversible signal-driven proposals, guardrailed A/B, approval-gated promotion + one-call
rollback, full audit, tested ≥90%, existing prompt tests green, PR reviewed.
