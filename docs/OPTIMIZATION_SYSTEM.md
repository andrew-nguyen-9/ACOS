# ACOS Optimization System

The Controlled Autonomous Optimization System (Phase 8) lets ACOS improve its own
resume, ATS, RAG, cover-letter, and copilot behavior over time — **without ever
self-modifying unsupervised**. It learns from real application outcomes, proposes
explainable changes, and applies them only after a human approves.

---

## Safety Model — Four Invariants

Every optimization the system performs satisfies all four of these, enforced in code:

1. **Logged.** Every applied or reverted change writes an immutable row to
   `optimization_logs` (append-only — the repository exposes no update method).
2. **Explainable.** A proposal is invalid unless it carries non-empty `rationale`,
   `expected_impact`, `confidence_level`, and `risk_level`. Enforced twice: by DB
   `CheckConstraint`s and by the guardrail validator at creation time.
3. **Reversible.** Each apply records the prior value (`old_value`); a single
   `revert` call restores it. Prompts are versioned, never overwritten — reverting a
   prompt re-activates the prior version.
4. **Approval-gated.** No change reaches production config without an explicit user
   approval action. `Applier.apply()` raises `ApprovalRequired` (HTTP 409) unless the
   proposal's `status == "approved"`.

> **Primary objective: interview rate, not ATS score.** The guardrail validator
> rejects any ATS-engine proposal justified solely by raising the ATS score. "Interview
> rate" = fraction of applications reaching a strong signal (`phone_screen` or stronger).

---

## Data Model

| Table | Purpose |
|-------|---------|
| `optimization_proposals` | Proposed changes with full explainability; status `pending → approved → (applied) → reverted` or `rejected`. |
| `optimization_logs` | Append-only audit trail; one row per `applied`/`reverted` action with `old_value`/`new_value`. |
| `prompt_versions` | Versioned prompt bodies; unique `(prompt_name, version)`; single active version per prompt. |
| `ab_experiments` | A/B experiments; metric defaults to `interview_conversion_rate`; status `running`/`concluded`. |
| `ab_variants` | Variant A/B configs with `impressions`/`conversions` counters. |

Engine identifiers (the only valid `target_engine` values): `resume`, `ats`, `rag`,
`cover_letter`, `copilot`.

---

## Feedback Signals

The system learns only from `outcome_signals` (captured in Phase 6):

- **Strong signals** (count toward interview rate): `phone_screen`, `interview`,
  `final_round`, `offer`, `accepted`.
- **Weak / negative signals**: `applied` (neutral baseline), `no_response`, `rejected`.

---

## The Learning Loop

`LearningLoop` (`backend/services/optimization/loop.py`) fires after every
`learning_trigger_count` applications (a `system_config` value, default `5`):

1. **Evaluator** (`evaluator.py`) computes metrics from outcome data:
   interview rate, per-template effectiveness, per-industry effectiveness, and the
   Pearson correlation between ATS score and strong-signal outcomes.
2. **Recommender** (`recommender.py`) turns those metrics into candidate proposals via
   deterministic heuristics:
   - **Template switch** when the best template's interview rate beats the worst by
     ≥ 0.15 (both with enough samples).
   - **ATS recalibration** when ATS↔outcome correlation is near zero — lowers
     `ats_keyword_weight` (rationale explicitly cites interview rate, so it passes the
     guardrail).
   - **Industry emphasis** for industries converting at ≥ 50% interview rate.
3. Each surviving candidate is validated by the **guardrails** and persisted as a
   `pending` proposal. The loop never applies anything.

`POST /optimization/loop/run` runs `maybe_run()` — it executes the cycle only when the
trigger threshold is met, else returns `{"ran": false, "reason": ...}`.

---

## Approval Workflow

```
pending ──approve──▶ approved ──apply──▶ (applied, config changed, logged)
   │                                            │
   └──reject──▶ rejected                        └──revert──▶ reverted (config restored, logged)
```

- `apply` on a non-approved proposal → **HTTP 409** (`ApprovalRequired`).
- Re-applying an in-effect proposal is blocked; double-revert is blocked.
- Log ordering is deterministic (`created_at ASC`), so revert always restores the most
  recent applied value.

---

## Explainability Fields

Every proposal answers five questions:

| Field | Question |
|-------|----------|
| `target_parameter` + `proposed_value` | **What** changed |
| `rationale` | **Why** it changed |
| `expected_impact` | **Expected impact** |
| `confidence_level` | `verified` \| `strong_inference` \| `weak_inference` |
| `risk_level` | `low` \| `medium` \| `high` |
| `evidence_json` | The metrics that justified the proposal |

---

## A/B Testing

`ABTestingService` (`ab_testing.py`) compares two variants and is scored on **interview
conversion rate** — never ATS score:

- `create_experiment(name, target_engine, variant_a, variant_b)` → running experiment + A/B variants.
- `record_impression` / `record_conversion` increment counters.
- `conclude` picks the higher `conversions/impressions` (ties → variant A) and requires
  every variant to have at least one impression (else `ValueError` → HTTP 409).

---

## Prompt Versioning

`PromptEvolver` (`prompt_evolver.py`):

- `seed_from_disk(name)` imports the on-disk YAML as version `1.0` (idempotent; active
  only if no active version exists).
- `create_variant(name, content, rationale)` adds a new **inactive** version with an
  auto-incremented minor version (`1.0 → 1.1 → 1.10`) and `parent_version` set.
- `activate(version_id)` enforces a single active version per prompt; prior versions are
  retained, so reverting a prompt = re-activating the previous version.

---

## API Reference

All routes are under `/api/v1`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/optimization/proposals?status=` | List proposals (optionally filtered by status) |
| POST | `/optimization/proposals/generate` | Run the Recommender, create pending proposals |
| POST | `/optimization/proposals/{id}/approve` | Approve a pending proposal |
| POST | `/optimization/proposals/{id}/reject` | Reject a pending proposal |
| POST | `/optimization/proposals/{id}/apply` | Apply an approved proposal (409 if not approved) |
| POST | `/optimization/proposals/{id}/revert` | Revert an applied proposal |
| GET | `/optimization/logs?limit=` | Recent audit-log entries |
| POST | `/optimization/loop/run` | Run the learning loop if the trigger is met |
| POST | `/optimization/experiments` | Create an A/B experiment |
| GET | `/optimization/experiments` | List experiments with variant stats |
| POST | `/optimization/experiments/variants/{id}/impression` | Record an impression |
| POST | `/optimization/experiments/variants/{id}/conversion` | Record a conversion |
| POST | `/optimization/experiments/{id}/conclude` | Conclude and pick the winner |
| GET | `/optimization/prompts/{name}/versions` | List versions of a prompt |
| POST | `/optimization/prompts/{name}/seed` | Seed a prompt from disk |
| POST | `/optimization/prompts/versions/{id}/activate` | Activate (or revert to) a version |

---

## Guardrails

`validate_proposal()` (`guardrails.py`) rejects a proposal (`GuardrailViolation`) when:

1. Any required field is missing or empty.
2. `confidence_level`, `risk_level`, or `target_engine` is outside its allowed set.
3. **ATS-only optimization:** the proposal targets the ATS engine and mentions raising
   the ATS score but mentions none of `interview` / `conversion` / `callback` / `recruiter`.
4. The proposal is `high` risk with only `weak_inference` confidence (too speculative).

The system never deletes prior prompt versions, never overwrites prompts in place, and
never changes production config without an approved, logged, reversible proposal.

---

## Phase 12 token-efficient workflow (dev process, not product code)

> This section is the **development working agreement** for Phase 12, not part of the
> product's self-optimization system above. It is documented here per the 12.0 spec so
> every later segment runs the same low-token loop. It changes no shipped behavior.

Phase 12 is large (17 segments, 12.0–12.16). To minimize Claude token spend per segment,
the dev loop runs under four cooperating tools. Each segment follows this loop.

| Tool | Role in Phase 12 | How it saves tokens |
|------|------------------|---------------------|
| **RTK** (Rust Token Killer) | CLI proxy; `git`/test/build commands are hook-rewritten to `rtk <cmd>` transparently. | Filters verbose command output (60–90% fewer output tokens on dev ops); confirm active with `rtk --version`. |
| **Caveman** | Terse assistant prose during implementation. | Drops articles/filler/hedging from explanations. **Code, commits, PRs, and security/irreversible-action text stay normal prose.** |
| **Ponytail** | Laziness ladder on every segment: YAGNI → stdlib → native platform → existing dep → one line → minimal new code. | Less code written = less to read, test, and review. Mark deliberate simplifications with a `ponytail:` comment naming the ceiling + upgrade path. |
| **Superpowers** | Enforced per segment: `test-driven-development` (tests before impl — CLAUDE.md rule 2), `systematic-debugging`, `verification-before-completion` (real, pasted, dated numbers), `requesting-code-review`. | Prevents rework; verification-before-completion stops false "done" claims that cost re-investigation. |
| `context7` | All framework APIs (uvloop / aiosqlite / FastAPI streaming / Chroma / Ollama / FTS5) and patched dependency ranges — never from memory (CLAUDE.md rule 4). | One authoritative fetch instead of trial-and-error against the wrong API surface. |
| `ralph-loop` / `ralph-skills` | Flywheel track (12.10–12.13): optimization-loop + skill-ROI scaffolding. | Reused loop structure instead of bespoke per-segment harnesses. |
| `skill-creator` | Flywheel ontology expansion (skill taxonomy growth, 12.11/12.12). | — |

**Per-segment loop:**

1. Open the single segment spec (`docs/superpowers/plans/2026-06-22-phase-12-N-*.md`) — self-contained, minimal archaeology.
2. Confirm the prior segment's Definition of Done is met.
3. TDD: write the failing test first, then the minimum code (Ponytail ladder).
4. Run the perf harness **before and after**; attach the delta to the PR (`docs/PERFORMANCE_LOG.md`).
5. `security-review` any file-I/O / user-input / dependency change.
6. `verification-before-completion` before claiming done — paste the real command output.

This is a workflow constraint only; 12.0 documents it and later segments follow it.
