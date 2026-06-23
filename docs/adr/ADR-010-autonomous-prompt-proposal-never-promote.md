# ADR-010: Autonomous Prompt-Proposal Loop — Propose-Only, Never Promote

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 13.6

---

## Context

Phase 12.13 (`PromptEvolutionService`) made prompt evolution **versioned, reversible,
approval-gated**: a candidate is a new inactive `PromptVersion`; only an explicit
`promote(approved_by=...)` flips the active pointer. Phase 13.4 added the human review
queue (`PromptReview.tsx` + `GET /flywheel/prompt/versions`) where a person approves or
rejects candidates.

13.6 adds the missing front end of that pipeline: an **autonomous** watcher that reads
success signals and, when a prompt underperforms, *creates a candidate on its own*. This
introduces machine autonomy into a system that was previously human-initiated end to end.
Autonomy near a production-affecting surface (the active prompt) is a boundary decision, so
it gets an explicit, enforced contract rather than per-call discipline.

---

## Decision

### 1. The loop proposes; it never promotes

`EvolutionLoop.run()` may call `PromptEvolutionService.propose` (writes an **inactive**
candidate) and, optionally, `trial` (an A/B experiment that records, never activates). It
has **no code path to `promote`**. Promotion remains exclusively human, via the 13.4
queue. This is the whole boundary: the autonomous component can *suggest* but never
*ship*. A unit test asserts `promote` is never invoked during a loop run, and that the
active-version pointer is unchanged after proposals are queued.

### 2. Every auto-proposal passes the existing guardrails

The loop reuses `PromptEvolutionService.propose`, which already runs
`optimization.guardrails.validate_proposal`. A `GuardrailViolation` drops that one
proposal and the loop continues — a vetoed candidate is never persisted. The loop adds no
new guardrail logic; it inherits the one source of truth.

### 3. Off the hot path

The loop runs **on demand / on a schedule**, never inside a generation request. It is
triggered by `POST /flywheel/prompt/auto-propose` (mirroring `POST /maintenance/generate`,
12.11/11.x), not wired into resume/cover-letter/copilot generation. Active-prompt
resolution on the hot path stays an O(1) pointer read (`get_active`); the watcher's
signal scan imposes zero per-request cost. There is no background cron — single-process
desktop app — so "scheduled" means an explicit trigger the app (or the user) invokes.

### 4. Explainable and idempotent

Each proposal links the signal ids that motivated it (carried in `change_rationale` as
`… | signals: <ids>`, the 12.13/13.4 convention). The loop is idempotent over a signal
window: before proposing for a prompt it checks existing candidates and skips if a
candidate already links the same signal set, so re-running the loop on an unchanged window
spawns no duplicates.

### 5. Input contract: prompt-performance signals

The watcher consumes `Signal` rows with `entity_type == "prompt"`, `entity_id ==
<prompt_name>` (e.g. `resume/extract_keywords`), whose `value` is a quality/outcome score.
It proposes when `n >= min_n` (default 5 — a 1-sample average is noise, ADR-009/12.10
Trap-3) **and** `avg_value < threshold`. Emission of those signals from the generation
write paths is a separate, future hook; defining the watcher's input contract here does
not fabricate data (CLAUDE.md #1) — absent such signals, the loop proposes nothing.

### 6. Candidate content generation is injected, default is a deterministic nudge

12.13 left *what the new prompt text is* to a human. The loop needs `proposed_content` to
call `propose`, so it takes an injectable `candidate_fn(prompt_name, active_content,
group)`. The default appends a deterministic guidance line to the active prompt — a
concrete, trial-able, human-reviewable candidate, **not** an LLM rewrite. An LLM rewriter
can replace `candidate_fn` later without touching the boundary.

---

## Consequences

**Positive**
- The flywheel closes itself: signals → candidate → human review, with the human gate intact.
- One guardrail source of truth; autonomy cannot bypass it.
- No hot-path cost; no silent production mutation.

**Negative / accepted**
- Default candidates are heuristic nudges, not novel rewrites — until a generator is wired,
  the loop's value is "surface the underperformer for review," which is acceptable.
- Requires prompt-performance signal emission to be useful; until then it is a no-op.

**Boundary restated:** the autonomous loop is a *proposer*. The active prompt changes only
when a human approves. This ADR is the load-bearing statement that no machine path
promotes.
