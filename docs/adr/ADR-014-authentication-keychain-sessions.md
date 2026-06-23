# ADR-014: Real Authentication — Keychain-Backed Per-User Sessions

**Status:** Accepted (Phase 16.1)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 16.1 (gates Phase 16 isolation hardening)
**Supersedes:** ADR-008 (session-layer `X-Tenant-Id` unauthenticated selector)

---

## Context

ADR-008 chose an **unauthenticated** `X-Tenant-Id` selector — fine while ACOS was a
single-user local app with no network principals. Phase 16's brief is "safe for multi-user
deployment," and Phase 18 ships an alpha to real testers. An unauthenticated tenant selector
means any caller can name any tenant id and read that tenant's data — unacceptable once more
than one person's data lives on a machine or behind any listener.

The constraint that makes this *not* a cloud-auth problem: ACOS is local-first (ADR-001).
There is no server to hold password hashes, no third party to federate with. Auth must work
**offline, on-device**, with the OS as the trust root.

## Decision

1. **Per-user identity replaces the bare selector.** A tenant is now bound to an
   authenticated user. `X-Tenant-Id` is no longer a self-asserted header; it is derived from
   an authenticated session.

2. **macOS Keychain is the credential trust root.** The session secret / unlock key is stored
   in the system Keychain (via the Tauri/Rust boundary — `keyring`/Security framework), never
   in plaintext in SQLite or a dotfile. The user authenticates once per session; the backend
   sidecar receives a short-lived session token, not the long-lived secret.

3. **Session token gates every tenant-scoped route.** Middleware validates the session and
   resolves the tenant server-side. A request without a valid session resolves to **no
   tenant** (default-closed), not a fallback tenant.

4. **Local-first, no network auth.** No remote identity provider, no password reset server.
   Account recovery is the user's OS account + Keychain. This is the honest boundary: lose the
   machine + Keychain, lose access (and, if encryption is on per ADR-015, the data).

5. **Cross-platform framework, mac implementation.** The credential-store interface is
   abstracted so Windows Credential Manager / libsecret can back it later (Phase 18 prepares
   the Win/Linux framework); only the macOS Keychain path is implemented now.

## Consequences

**Positive** — closes the cross-tenant read hole ADR-008 left open; credentials never touch
the repo or disk in plaintext; works fully offline.

**Negative / accepted** — no cloud recovery (by design, ADR-001); the Keychain dependency
makes the Rust boundary load-bearing for security, so it gets `security-review`. Adds a login
step to a previously frictionless local app — acceptable for multi-user/alpha.

**Relation:** enables ADR-015 (encryption key can be Keychain-bound) and is the precondition
for Phase-16 isolation hardening and Phase-18 multi-user safe mode. Supersedes ADR-008's
"authn deferred" forward-looking note.
