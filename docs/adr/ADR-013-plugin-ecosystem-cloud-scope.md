# ADR-013: Plugin / Ecosystem / Cloud Scope — Deliberate Deferral

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 14.3

---

## Context

The original brief lists, as "platform" requirements: a runtime **plugin system**
(registry / lifecycle / permissions / isolation), a **local + cloud hybrid** mode,
**ecosystem readiness** (third-party plugins, job-board / external-ATS integrations,
public **API exposure**). ACOS as shipped (Phases 0–13) is a **single-user, local-first**
desktop app (ADR-001) with **no inbound network listener for other principals**
(ADR-008) and exactly **one** outbound channel — the signed auto-updater (ADR-011).

The burden of proof is on *building*, not on deferring (ponytail rung 1): a feature is
added when a concrete need exists, not because a brief enumerated it. None of these four
items has a present need for a single-user local app, and each adds a large, security-
sensitive surface. This ADR records the deferral explicitly so the items are **on the
books as deferred, not silently dropped**, and formalizes the boundary that *actually*
governs extension in this repo.

## Decision

### 1. No runtime plugin engine — the service-module boundary is the contract

There is **no** dynamic plugin registry, loader, lifecycle manager, or permission
sandbox. Extension happens by adding a **service module** under `backend/services/<domain>/`
with a typed boundary, behind a route — the same way every engine (resume, ATS, RAG,
strategy, flywheel) was added. This is the boundary that isolates domains today; it needs
no runtime machinery because there is no untrusted third-party code to isolate.

The word "plugin" in this repo refers to the **Claude development workflow**
(`docs/07_PLUGIN_ORCHESTRATION.md`) — a build-time orchestration contract for *how
features are developed*, not a runtime extension engine. That document remains the
plugin contract that governs the repo.

### 2. No cloud sync / hybrid mode

Rejected outright. ADR-001 is local-first and the brief itself states cloud is "never
required." All data stays on the user's disk. The only outbound call remains ADR-011's
signed update fetch.

### 3. No public API-exposure layer, no third-party / job-board / external-ATS integrations

ACOS exposes a **localhost-only** FastAPI for its own Tauri frontend (ADR-007/008). It
does not listen for other principals, publish an API, or call out to job boards / ATS
vendors. Job ingestion stays **paste/saved-JD, local** (surfaced in Phase 15.1).

### 4. Security hardening + optional at-rest encryption (the only new code this ADR carries)

The existing ingest/path/exec defenses are reaffirmed by the 14.3 audit (see Consequences).
A **single new, optional** capability is added: opt-in **at-rest field encryption**
(`backend/security/encryption.py`, `EncryptedText`), **OFF by default**, gated on the
`cryptography` extra (`requirements-encryption.txt`) + `ACOS_ENCRYPTION_KEY`.

**Honest threat model (CLAUDE.md #1):** it mitigates **local-disk theft** as
defense-in-depth over macOS FileVault. It is **not** a multi-user, network, or in-memory
boundary — the key lives on the same machine and a running app holds plaintext. Primary
at-rest protection on the target platform remains **FileVault**.

## Consequences

**Positive**

- No speculative, security-sensitive surface (plugin sandbox, public API, cloud sync) is
  carried unbuilt and unmaintained.
- The boundary that governs extension is the one that already exists and is tested.
- Users who want at-rest field encryption can opt in without every install paying for a
  C-extension dependency.

**Negative / accepted**

- A genuine third-party extension, multi-device sync, or external job-board integration
  would each require new design + its own ADR before any code.
- Opt-in encryption is one-way in practice (encrypt-in-place of old rows is a batch job,
  not built); toggling the flag back off after writing tokens surfaces ciphertext on read.

**14.3 audit result (reaffirmed, not new code):**

- File ingest flows through `backend/ingestion/security.py` (path allowlist + 50 MB size
  cap + checksum + filename sanitization); the asset:// scheme through `lib.rs`
  `resolve_asset_path` (canonicalize + `starts_with`, symlink-safe, default-closed).
- **No `eval` / `exec` / `pickle` / `os.system` / `subprocess`** on parsed content or
  user input anywhere in backend application code.
- No path bypasses these chokepoints.

## Reopen conditions

| Deferred item | Reopen when |
|---|---|
| Runtime plugin engine (registry/lifecycle/permissions/isolation) | a real third-party extension must run untrusted code |
| Cloud sync / hybrid mode | a user explicitly opts into multi-device sync |
| Public API exposure · third-party / job-board / external-ATS integrations | network exposure for other principals / multi-user is chosen |
| App-level encryption beyond opt-in field encryption (e.g. full-DB SQLCipher) | a non-FileVault or shared-disk target is required |

Each reopen is its own brainstorm + ADR — none is implied by this one.

## Relationships

- Extends **ADR-001** (local-first) and **ADR-008** (no inbound network boundary).
- Leans on **ADR-011** (the single outbound channel stays the only one).
- Mirrors **ADR-010**'s "defer the powerful thing until a concrete need" posture.
