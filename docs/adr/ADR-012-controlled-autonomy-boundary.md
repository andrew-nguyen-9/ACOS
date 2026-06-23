# ADR-012: Controlled-Autonomy Boundary — Recommend, Never Act

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 15.1 (gates all of Phase 15)

---

## Context

Phase 15 turns ACOS into a *career agent*: it ranks jobs, recommends Apply/Skip/Tailor,
simulates interviews, and composes a daily briefing. Every one of those surfaces consumes
an engine that already exists (Phase 9 strategy, Phase 12 flywheel, the questions/KG
stack) — Phase 15 *surfaces and orchestrates*, it does not build new decision engines.

An "agent" implies autonomy, and autonomy near a person's career and external systems
(job boards, recruiters, email) is a boundary decision. ADR-010 already drew the analogous
line for the prompt-evolution loop — *it proposes, it never promotes; a human gate is the
only path that ships a change, and a test asserts no machine path bypasses it*. ADR-012
generalizes that precedent from one loop to the entire Phase-15 agent layer.

This ADR is written **before any Phase-15 agent surface** (15.1) and ratified in close-out
(14-15.8). Later segments (15.2 suggestion, 15.3 interview sim, 15.4 briefing) cite it
rather than re-deciding it.

---

## Decision

### 1. What the agent MAY do

Rank · recommend · generate · simulate · explain. All of it is **read + compute +
present**: scoring a JD, ordering jobs by fit, recommending a resume version or cover-letter
tone, simulating a recruiter and evaluating an answer against the knowledge graph, composing
a briefing from existing engine outputs. These produce *information the user acts on*.

### 2. What the agent MAY NOT do

Submit an application · contact a recruiter or any third party · modify an external system ·
act without explicit user approval. There is **no code path** in the agent surfaces that
performs an outbound action against an external principal. Not "guarded," not "disabled by a
flag" — **absent**. The app has no network listener for other principals (ADR-008) and no
outbound job-board / ATS / email integration (ADR-013 records that deferral); ADR-012 is the
product commitment that those stay absent in the agent layer.

### 3. The boundary is enforced by absence, and a test asserts it

Mirroring ADR-010's never-promote test: a unit test scans the agent-surface modules
(strategy prioritization + suggestion, interview simulation, briefing orchestrator) and
asserts none of them reference an outbound-action capability — no HTTP client posting to an
external host, no `submit_application` / `contact_recruiter` / `send_*` symbol, no job-board
SDK. The test fails the moment such a path is introduced. This is the load-bearing
guarantee: the boundary is checkable in CI, not just documented.

### 4. "Action" buttons are internal-only

Phase-15 UI has affordances labelled *Apply*, *Tailor*, *Follow up*. These are **internal
state transitions**: *Apply* marks the application's `status` and/or opens the existing
in-app compose/tailor flow; *Follow up* surfaces a reminder. None of them POSTs to a job
board or sends a message. The label describes the user's intent; the code does a local
mutation the user could do by hand. A test asserts the surface exposes no external-submit
affordance.

### 5. Every recommendation is explained and confidence-tagged (ADR-006)

No bare verdicts. A ranking, an Apply/Skip/Tailor call, a success/interview probability, an
answer score — each carries its `verified` / `strong_inference` / `weak_inference`
confidence and the evidence it derived from (matched/missing skills, risk factors, KG node
coverage, signal sample size). Estimates are labelled estimates, never bare numbers. Low-n
(`weak_inference`) recommendations are de-emphasized — excluded from "top pick" emphasis —
so the user is never nudged hard on thin evidence.

### 6. Server-ranked, deterministic

Ordering is the engine's, computed server-side and rendered in that order. Surfaces do not
re-rank client-side; a given input yields a stable order. This keeps the recommendation
auditable — what the user sees is exactly what the engine decided.

### 7. Off the hot path (orchestrators)

Composed surfaces that roll up multiple engines (15.4 briefing) run **on demand / on a
schedule via the existing 13.6 evolution-loop seam**, never inside a generation request.
They add zero per-request latency to resume/cover-letter/copilot generation (asserted).

---

## Consequences

**Positive**
- One stated, testable boundary that every Phase-15 surface inherits — no per-segment
  re-litigation of "can the agent submit this?".
- The safety property is structural (no path exists) and CI-checkable, not reliant on
  reviewer vigilance.
- Recommendations stay explainable and honest about uncertainty (ADR-006), so the human
  stays the decision-maker.

**Negative / accepted**
- The user does the final submit/outreach by hand, always. That is the product decision, not
  a missing feature — auto-apply and recruiter outreach are out of scope **by decision**
  (recorded deferred-never in the roadmap).
- A future real integration (e.g. an opt-in job-board export) would require its own ADR that
  explicitly amends this boundary; it cannot be added silently because the absence test would
  fail.

**Boundary restated:** ACOS recommends; it never acts. No auto-apply, no recruiter outreach,
no external mutation. The human approves and executes every outbound action. This ADR is the
load-bearing statement that no agent path acts on the user's behalf against an external system.
