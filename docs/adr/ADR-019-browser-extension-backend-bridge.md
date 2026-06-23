# ADR-019: Browser Extension ↔ Backend Bridge — Paired, Local, App-Gated

**Status:** Accepted (Phase 17.1)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 17.1 (gates Phase 17)

---

## Context

Phase 17 adds Chrome + Firefox extensions that capture a job posting from the current page and
send it to ACOS. That requires the extension (running in the browser) to talk to the ACOS
backend (a Python sidecar the Tauri app spawns on localhost). This is the first time ACOS
exposes its local API to *another process*, so the trust boundary needs a decision.

Constraints from the brief + answers: local-first, no background tracking, no browsing-history
collection, only explicit user-triggered capture (Q6: one-time token pairing, extension active
only when the app is running; Q9: no web-store publish — installed via the app's wizard).

## Decision

1. **One-time token pairing.** On first connect, the app generates a pairing token (shown in
   the install wizard / Settings); the user pastes it into the extension once. The extension
   stores the token and presents it on every request. The backend rejects unpaired requests.
   No token = no access (default-closed). This stops any random web page or other extension
   from hitting `localhost` and reading the user's data.

2. **App-gated: the bridge exists only while the app runs.** The backend sidecar is alive only
   when the Tauri app is running (it spawns/owns it — `lib.rs`). The extension detects
   "backend unreachable" and degrades to "capture queued, open ACOS to sync." There is **no
   always-on listener** when the app is closed.

3. **Localhost-only, origin-checked, narrow CORS.** The bridge binds loopback only; CORS
   allows exactly the extension origin(s). No remote host can reach it. This is consistent with
   ADR-008-successor (no network principals beyond the paired, authenticated local user).

4. **Capture is explicit and job-scoped only.** The extension acts **only** on an explicit
   user click; it extracts job-posting content (title, company, responsibilities,
   qualifications) and nothing else — no history, no cookies, no unrelated page scraping, no
   background reads. Captured text passes the ADR-017 ingestion-time injection screen before
   it touches ACOS.

5. **Recommend-never-act preserved (ADR-012).** Capture creates an *application draft* the user
   reviews; it does not submit anything anywhere. The extension is an *input* path, not an
   action path.

## Consequences

**Positive** — the local API is exposed safely (paired + loopback + app-gated + origin-checked);
no privacy surface beyond explicit job capture; honors local-first with the cloud-sync door
shut (disabled by default, future per ADR-013/v2).

**Negative / accepted** — pairing is a one-time manual step (friction traded for safety);
capture only works while the app is open (queue-and-sync otherwise); sideload install (no web
store) means manual update of the extension — acceptable for alpha (Q9).

**Relation:** capture flows into the existing `backend/ingestion/jobs.py` + normalizer;
injection screen = ADR-017; no-submit boundary = ADR-012.
