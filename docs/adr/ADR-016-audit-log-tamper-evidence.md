# ADR-016: Audit Logging — Tamper-Evident, User-Owned, Configurable Strictness

**Status:** Accepted (Phase 16.3)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 16.3

---

## Context

Phase 16's brief: log every generation request, retrieval, ATS scoring action, and
optimization recommendation; "logs must be immutable." The literal word *immutable* is
impossible to honor for a file the user fully owns on their own disk — they can `rm` the
database. So the real, honest property is **tamper-evident**, not tamper-*proof*: any
modification or deletion is *detectable*, even though a determined owner can still do it.

The user also wants control (Q3): "sometimes a user wants to customize which [actions] they
are allowed to do, with risk of breaking the system." So strictness is **configurable**, with
the risk surfaced.

## Decision

1. **Append-only audit table with a hash chain.** Each audit row stores `prev_hash` and
   `row_hash = H(prev_hash ‖ canonical(row))`. Any edit/deletion of a past row breaks the
   chain from that point forward — detectable by a `verify_audit_chain()` check. This is the
   tamper-evidence mechanism: cheap, local, no external timestamp authority.

2. **What is logged (content-light).** Event type, tenant, timestamp, operation
   (generation / retrieval / ATS-score / optimization-recommendation), input/output *digests
   + metadata* (model, prompt-version, confidence) — **not** full prompt/response bodies by
   default (privacy + size). A verbose mode can include bodies when the user opts in.

3. **No unlogged inference (strict rule).** Every generation/retrieval/ATS/optimization path
   writes an audit row. A test asserts the chokepoints emit audit events; a path that skips
   the log is a bug.

4. **Configurable strictness, risk surfaced.** Settings expose the audit policy:
   - `enforced` (default): the chain is verified on startup; tampering raises a visible
     warning; the app refuses silent corruption.
   - `relaxed`: the user may prune/disable logging — the UI states plainly this **breaks
     tamper-evidence and is at their own risk** (Q3). We let them; we do not pretend it's safe.

5. **Off the hot path.** Audit writes are cheap (one insert) but batched/async where they'd
   add latency to a generation request; verification runs on startup/schedule, not per request.

## Consequences

**Positive** — every inference is accountable and auditable; tampering is detectable via one
chain check; honest about what "immutable" can mean for user-owned local data; the user keeps
control (their machine, their rules) with the risk made explicit.

**Negative / accepted** — a hash chain detects but cannot *prevent* deletion by the owner (by
nature of local-first); verbose body-logging trades privacy/size for completeness, so it's
opt-in. Relaxed mode can disable the guarantee — accepted as the user's informed choice.

**Relation:** content digests respect ADR-015 encryption (no plaintext leakage into the log);
audit events feed Phase-18 local-only telemetry aggregates (counts, never bodies).
