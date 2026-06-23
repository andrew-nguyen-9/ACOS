# ADR-020: Alpha Distribution, Update Channel & Feature-Flag Rollout

**Status:** Accepted (Phase 18)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 18 (distribution + rollout segments)
**Builds on:** ADR-011 (background-update network boundary), ADR-001 (local-first)

---

## Context

Phase 18 ships ACOS to alpha testers. The brief wants versioned builds, rollback, staged
rollout, feature flags, A/B, a signed DMG, and an update mechanism — with strict rules: no
silent updates, no forced updates, no breaking changes without migration. Answers narrow it:
macOS DMG now + Win/Linux *framework* (Q10); manual download + in-app "update available" check,
GitHub-Releases door kept open (Q12); **no Apple Developer ID cert available** (Q13); local
feature flags with deterministic-hash A/B (Q14).

## Decision

1. **Alpha = unsigned/ad-hoc macOS DMG, manual download.** With no Developer ID (Q13), the DMG
   is **not notarized**; Gatekeeper will quarantine it. We document the honest workaround
   (right-click → Open, or `xattr -d com.apple.quarantine`) in `PACKAGING.md` rather than
   pretend it's signed. Distribution is a manual download link for alpha.

2. **Update = check, never push (ADR-011 honored).** The app does an **in-app "update
   available" check** against a version manifest and tells the user; it **never** downloads or
   installs silently or forcibly. The user chooses to update. The manifest source is pluggable;
   **GitHub Releases is the intended backend** but the door stays open — alpha can run off a
   static manifest. One signed, TLS-only, data-free channel (ADR-011) — only a version string
   crosses it.

3. **Versioning + rollback on the 14.1 spine.** Every build carries the 14.1 semantic version +
   migration head. Rollback = reinstall a prior DMG + Alembic `downgrade` to that version's
   head; **no breaking change ships without a down-migration** (strict rule). Versioned builds
   are retained so a tester can roll back.

4. **Feature flags: local, deterministic, no server.** Flags live in a local config (per
   install / per tenant). Staged rollout + A/B use a **deterministic hash** of (tenant-id ‖
   flag-key) → stable bucket, so assignment is reproducible offline with no assignment server
   (Q14). A broken feature is killed by flipping its flag (safe rollback without a rebuild).

5. **Cross-platform framework, mac build.** Build/flag/update interfaces are platform-abstract;
   only macOS is built and verified now. Win/Linux DMG-equivalents are scaffolded (Tauri
   targets configured, not released) for a later alpha (Q10).

## Consequences

**Positive** — testers get versioned, rollback-able builds; updates are honest and user-
controlled (no silent/forced); features roll out and roll back via a flag flip, no rebuild;
offline-deterministic A/B needs no backend.

**Negative / accepted** — unsigned DMG = Gatekeeper friction documented, not hidden (the
honest cost of no cert); manual download/update for alpha (GitHub-Releases automation deferred,
door open); local flags mean no central kill-switch across installs — acceptable for a
local-first alpha.

**Relation:** honors ADR-011 (update channel) + ADR-001 (local-first); telemetry that measures
rollout is local-only aggregates (Phase 18, no PII out); multi-user safety = ADR-014 auth +
isolation.
