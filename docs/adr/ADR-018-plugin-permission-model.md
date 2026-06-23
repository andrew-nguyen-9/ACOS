# ADR-018: Permissioned Plugin Model — Capability Manifest, No Full-System Access

**Status:** Accepted (Phase 16.6)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 16.6
**Amends:** ADR-013 (deferred the runtime-plugin engine)

---

## Context

ADR-013 *deferred* a runtime plugin engine as speculative for a single-user local app. Phase
16's brief reopens it: "each plugin must declare allowed data access, allowed actions,
execution boundaries; no plugin has full system access." Q5: build it **if it won't seriously
impact functionality or usability**.

So this ADR partially amends ADR-013: we build the **permission model and manifest contract**
— the part that makes plugins *safe* — but stay on the lazy rung for the *runtime/sandbox
execution engine*, which is heavy and only pays off once real third-party plugins exist
(Phase-18 ecosystem-readiness records that as future/v2). The permission framework is cheap,
forward-compatible, and immediately useful for the *existing* internal service modules.

## Decision

1. **Every plugin/module declares a capability manifest.** A declarative manifest states:
   - `data_access`: which tenant-scoped resources it may read/write (resumes, applications,
     KG, signals…), least-privilege by default.
   - `actions`: which operations it may invoke.
   - `boundaries`: network (default none — local-first), filesystem (allowlisted paths only),
     execution limits.

2. **No full-system access — default-closed.** A plugin gets exactly what its manifest
   declares and nothing more. Unlisted access is denied, not warned. This applies first to the
   *existing internal service-module boundary* (formalizing what `docs/07` describes), so the
   contract is real and tested before any third party exists.

3. **Enforcement at the access boundary.** A permission check sits at the data/action layer;
   a plugin call outside its manifest raises, and a test asserts denial. The manifest is the
   single source of truth — no implicit grants.

4. **Runtime third-party execution engine stays deferred.** We do **not** build a sandboxed
   process/WASM loader for untrusted third-party code now. The manifest schema is designed so
   that engine can attach later without a redesign. Ecosystem/marketplace = future (v2).

## Consequences

**Positive** — a checkable least-privilege contract now, with no heavy runtime; the existing
service modules gain an enforced boundary; forward-compatible with a real plugin engine.

**Negative / accepted** — without a runtime sandbox this governs *trusted internal* modules,
not yet *untrusted third-party* code (honest scope — don't claim sandbox isolation we didn't
build). The manifest adds declaration overhead to each module — minor, and it documents the
boundary anyway.

**Relation:** amends ADR-013's deferral (permission model now, runtime engine still later);
permission denials are audited (ADR-016); aligns with ADR-008-successor tenant isolation.
