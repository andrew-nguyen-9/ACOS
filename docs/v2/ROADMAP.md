# ACOS v2 Roadmap (post-Phase-18, emergent)

v1 is the planned arc, **Phases 0–18**. v2 is everything after — **adhoc, demand-driven**,
not a fixed phase ladder. This file holds *candidate themes only*; nothing here is committed.
A theme becomes a phase when a [`BACKLOG.md`](../BACKLOG.md) batch crosses S1/S2, or an
[`IDEAS.md`](IDEAS.md) entry earns a sponsor (real user demand).

## Where v2 phases come from

```
IDEAS.md (raw)  ──graduate──▶  this ROADMAP (candidate theme)  ──batch──▶  phase-NN plan
BACKLOG.md (bugs/issues) ─────────────────────────────────────▶  phase-NN plan
```

ADRs continue the single immutable sequence in [`../adr/`](../adr/) (ADR-014+). v2 does not
fork ADR numbering.

## Candidate themes (unordered, uncommitted)

Each links back to the v1 decision it would re-open or the gap it fills.

| Theme | Re-opens / fills | One-line scope |
|-------|------------------|----------------|
| **Cloud sync (opt-in)** | ADR-013 (deferred), ADR-001 (local-first) | E2E-encrypted optional sync of tenant data across devices; off by default. |
| **Runtime plugin engine + marketplace** | ADR-018 (model built, engine deferred) | Sandboxed third-party plugin loader honoring the Phase-16 capability manifest. |
| **ATS / job-board integrations** | Phase 17 extension | Direct connectors (Greenhouse, Lever, LinkedIn) beyond browser capture; outbound + per-vendor, opt-in-export only. |
| **Mobile / web client** | ADR-005 (Tauri desktop) | Read-mostly companion surfacing the same local-first data. |
| **Team / enterprise mode** | ADR-008, ADR-009 | Shared org tenants, role-based access, admin audit views. |
| **Cross-platform builds** | macOS-locked packaging | Windows + Linux distribution if alpha demand appears. |

## Status

**v1 COMPLETE (Phases 0–18 shipped, 2026-06-23).** Final v1 state: local-first AI career OS ·
recommend-never-act agent (ADR-012) · multi-tenant w/ real auth + isolation (ADR-014) ·
tamper-evident audit + injection defense + at-rest encryption (ADR-015/016/017) · capability
permission model (ADR-018) · browser job-capture (ADR-019) · alpha-distributable, unsigned DMG +
notify-only update + local feature flags (ADR-020). Everything in the table above is **deferred to
v2** — recorded, not dropped (Phase 18.6 ecosystem-readiness recon). No v2 phase is scheduled until
the first adhoc batch forms.
