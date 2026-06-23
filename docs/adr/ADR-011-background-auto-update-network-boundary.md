# ADR-011: Background Auto-Update — A Single, Signed, Documented Network Channel

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 13.9

---

## Context

ACOS is local-first and, until now, **strictly no-network during operation**
(CLAUDE.md "Local only: No data transmitted to external services"; ADR-001). Phase
13.9 adds **background auto-update** to the packaged app so users get fixes without
re-downloading a DMG. An auto-updater must reach the network to check for and fetch a
new version. This **deliberately overrides** the no-network default — by explicit user
decision — and so requires an ADR that draws the boundary precisely and an enforced,
auditable contract. This is the load-bearing decision; everything else in 13.9
implements it.

---

## Decision

### 1. The override is narrow and explicit

The local-only rule is overridden **for the update channel only**. The *only* outbound
network calls ACOS makes are:
1. the update **check** (GET a static JSON manifest), and
2. the update **artifact fetch** (GET the new bundle) when an update is applied.

No telemetry, no analytics, no identity, no usage data, no `X-Tenant-Id` on the wire
(ADR-008 §Forward-looking authn stays non-live). Everything else — inference,
retrieval, generation, signals, the flywheel — remains entirely local. The update
check carries only the current version in the URL path; it sends no user data.

### 2. Signature verification before apply (the security crux)

Updates are signed with a Tauri/minisign **private key held out-of-repo**. The
corresponding **public key is bundled** in `tauri.conf.json > plugins.updater.pubkey`.
The Tauri updater verifies the artifact's signature against that bundled public key
**before** applying it; a tampered or unsigned artifact **fails verification and is not
installed**. An attacker who controls the update endpoint (or the network) cannot push
a malicious build without the private key. The private key is **never committed**
(CLAUDE.md): if it leaks, rotate; if it is lost, updates stop — both acceptable versus
shipping unsigned auto-updates.

### 3. TLS + minimal surface

The endpoint is HTTPS only. CSP `connect-src` is relaxed to add **exactly one** origin
— the update host — alongside the existing `http://localhost:8000` backend. No other
origin is permitted. This single relaxation is documented in `tauri.conf.json` and
`docs/PACKAGING.md`.

### 4. Consent-visible, not silent surveillance

The check may run in the background, but the update is **user-visible**: a release-notes
surface shows the new version + notes, and the user triggers install/relaunch. The app
is honest that it now talks to one network endpoint; this is not hidden.

### 5. Rollback / atomicity

The Tauri updater applies atomically — a failed download or verification leaves the
installed app intact (no half-written binary). A failed update must never brick the
app; the failure path leaves the current version running.

---

## Consequences

**Positive**
- Users get security/bug fixes without manual re-download.
- The network boundary is explicit, signed, TLS-only, and minimal — auditable in one place.

**Negative / accepted**
- ACOS is **no longer strictly no-network**: one signed update channel exists. Docs,
  README, and `MODEL_SETUP`/`PACKAGING` must state this plainly (no "fully offline"
  claim without the update-channel caveat).
- Requires operating an update endpoint + safeguarding the private signing key.
- ADR-008's deferred authn note is now **load-bearing**: because a network path exists,
  the "no auth, single-user, no `X-Tenant-Id` on the wire" assumption must be
  re-affirmed as still-true for everything except this one unauthenticated, data-free
  GET. Re-recorded as still-deferred in 13.11.

**Boundary restated:** ACOS makes exactly one kind of outbound call — a TLS GET to fetch
a **signature-verified** update. Anything else crossing the network is a regression
against this ADR.
