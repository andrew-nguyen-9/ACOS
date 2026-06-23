# ADR-017: Prompt-Injection Defense — Layered Detect / Flag / Block

**Status:** Accepted (Phase 16.4)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 16.4

---

## Context

ACOS ingests **untrusted text**: job descriptions pasted/captured from the web, PDFs/DOCX
uploaded by the user, and (Phase 17) extension-captured pages. Any of these can carry an
injection — "ignore previous instructions," a hidden instruction block in white-on-white PDF
text, a fake system prompt, or a data-exfiltration lure. Because that text flows into RAG
context and LLM prompts, an injection can hijack generation or try to leak other records.

The brief asks to detect/block malicious JDs, hidden PDF instructions, injected system
prompts, and exfiltration attempts. Q4: use a combination of approaches; pick the best for
this use case. No single technique is sufficient — heuristics miss novel phrasings, a
classifier needs training data, and LLM-screening costs latency. So: **layered, defense in
depth.**

## Decision

A **two-checkpoint, three-layer** pipeline. The combination chosen for a local, latency-
sensitive, no-training-data app:

**Checkpoints (where):**
- **Ingestion-time** — when a JD/PDF/page enters (`backend/ingestion/`): screen before the
  text is ever embedded or stored.
- **Prompt-assembly-time** — when retrieved context is composed into a prompt: a final guard
  on what actually reaches the model, with untrusted content fenced (delimited + role-marked
  as data, never instructions).

**Layers (how), cheapest first:**
1. **Heuristic / denylist (always on, ~free).** Pattern scan for known injection markers
   ("ignore previous", "system:", instruction-override verbs), invisible/zero-width chars,
   white-text/hidden-layer PDF extraction artifacts, suspicious URLs. Fast, catches the
   common cases, no model call.
2. **Local classifier (cheap).** A lightweight scorer (heuristic-weighted or a small local
   model) yields an injection-likelihood score for ambiguous text the denylist didn't settle.
3. **LLM-screening (opt-in / escalation only).** For high-ambiguity content, a local-LLM
   "is this trying to instruct the assistant?" screen — used sparingly because it adds
   latency (gated like Phase 12.8 structured-output: escalation, not default).

**Policy (what happens): flag by default, block on high confidence.**
- High-confidence injection → **block** (don't embed/store; surface to the user with why).
- Medium → **flag + sanitize** (strip the offending span, fence the rest as data, warn).
- Low → pass, but always fenced as untrusted data at prompt-assembly.
The default is **flag-and-fence over hard-block** so a legitimate-but-weird JD isn't lost;
hard-block is reserved for high confidence.

## Consequences

**Positive** — defense in depth; the cheap layer handles the common case with no latency, the
expensive layer is reserved for ambiguity; fencing untrusted content at assembly limits blast
radius even when detection misses; honest user-facing explanation of why something was blocked.

**Negative / accepted** — no detector is perfect; novel injections may pass the heuristics
(hence the always-on fencing as backstop). LLM-screening adds latency so it's escalation-only.
Denylists need maintenance — they live in a versioned list, updatable without code change.

**Relation:** feeds the ADR-016 audit log (blocked/flagged events are logged); Phase-17
extension capture runs the same ingestion-time checkpoint; adversarial test corpus
(Phase 16 close-out) exercises this layer.
