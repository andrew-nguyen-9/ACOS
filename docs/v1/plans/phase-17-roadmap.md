# Phase 17 — Browser Extension & Job-Capture Ecosystem (Roadmap)

> **STATUS (2026-06-23): SHIPPED on `feat/phase-17-browser-extension`** (stacked on phase-16,
> NOT pushed). All 5 segments: 17.1 scaffold+paired bridge (ADR-019 ratified) · 17.2 page
> capture/extraction (heuristic readability, pure+tested) · 17.3 normalization/enrichment
> (capture flows the existing ingestion→normalizer→Phase-9 path, no new engine) · 17.4 one-click
> Add→Application draft (review-not-submit, de-duped) · 17.5 UX + Settings pairing + Firefox
> single-source build + close-out. Bridge: paired (one-time token), localhost-only, app-gated,
> origin-checked CORS; capture passes the ADR-017 injection screen. New top-level `extension/`
> (MV3 + polyfill shim; `node --test` 4 green; `npm run build` → dist/chrome + dist/firefox).
> Backend 8 bridge tests, suite 1155 green, 141 vitest, tsc/pyright clean. Deferred: site-specific
> parsers, ATS/job-board APIs, web-store listing, cloud sync.

**Branch:** `feat/phase-17-browser-extension` (cut off `main` after Phase 16 merges).
**Predecessor:** Phases 0–16 shipped. Exists: job ingestion (`backend/ingestion/jobs.py`,
`normalizer.py`, `entity_extractor.py`), `routes/ingestion.py`, application drafts
(`models/application.py`), enrichment engines (Phase 9 `role_fit_scorer`, `skill_gap_forecaster`),
injection screen (16.4, ADR-017), auth + paired-bridge model (16.1).
**Phase ends at 17.5 (close-out).** No 17.6+.

---

## Why this is a new *front-end*, not a new pipeline

ACOS already ingests, normalizes, enriches, and drafts applications from pasted JDs. Phase 17
adds a **browser capture surface** that feeds the *same* pipeline — the extension is an input
path, not a parallel system. Net-new = the extension itself (MV3 + Firefox), the page-extraction
logic, and the secure bridge (ADR-019). Normalization/enrichment/draft-creation = surface
existing engines.

## Reconciliation — brief vs shipped reality

| Brief item | Shipped already | Phase 17 disposition |
|---|---|---|
| 1. Browser extension (Chrome + Firefox); extract title/company/responsibilities/qualifications | none | **NEW** MV3 + webextension-polyfill single source → 17.1/17.2. |
| 2. Structured job normalization (schema / skill extraction / ATS-ready) | `ingestion/jobs.py` + `normalizer.py` + `entity_extractor.py`; ATS engine | **Surface** existing normalizer; map captured → standard schema → 17.3. |
| 3. One-click "Add to ACOS" → auto-create application draft | `routes/ingestion.py` + `Application` draft status | **Wire** capture → ingestion route → draft → 17.4. |
| 4. Job enrichment (industry / skill graph / seniority / ATS keywords) | Phase 9 enrichment + ATS keyword extraction | **Surface** existing enrichment on captured jobs → 17.3. |
| 5. Cross-system sync (local-first; cloud disabled) | local backend on localhost; no cloud | **Paired localhost bridge** (ADR-019); cloud stays disabled → 17.1. |
| 6. Security (sanitize / no injection / no sensitive browser data / job-only) | ADR-017 injection screen (16.4); ADR-019 bridge model | **Apply** injection screen at capture + explicit-capture-only + origin/token → 17.1/17.2. |

## Segment map (dependency-ordered) — 5 segments

```
17.1  Extension scaffold + paired backend bridge (ADR-019)   ← 16 ✓   FIRST; MV3 + polyfill workspace, one-time token, localhost CORS, app-gated
17.2  Page capture + extraction                              ← 17.1   content script; heuristic readability + local-LLM fallback (Q8); sanitize + injection screen
17.3  Normalization + enrichment                             ← 17.2   map → standard schema via existing normalizer; surface Phase-9 enrichment + ATS keywords
17.4  One-click Add to ACOS → application draft              ← 17.3   capture → ingestion route → Application draft; review-not-submit (ADR-012)
17.5  Extension UX + install-wizard + Firefox parity + close ← 17.4   frontend-design UX; sideload toggle in wizard/Settings; Firefox build; security-review; merge
```

**Critical path:** `17.1 → 17.2 → 17.3 → 17.4 → 17.5`. The bridge (ADR-019) gates everything —
no capture leaves the browser until the paired, app-gated channel exists.

## ADRs this phase produces

- **ADR-019** — Browser-extension ↔ backend bridge (one-time token pairing, localhost-only,
  app-gated, origin-checked, explicit-capture-only, no background tracking). 17.1.

## Carried-forward gates (every applicable segment)

- **No background tracking, no browsing-history collection, no unrelated scraping, explicit
  user-triggered capture only** (Phase-17 strict rules) — asserted by tests (the extension acts
  only on click; a test confirms no history/tab/cookie access in the manifest permissions).
- **Captured content passes the ADR-017 injection screen** before touching ACOS; **no-submit
  boundary (ADR-012)** — capture creates a draft, never submits.
- **TDD**: Playwright for extension behavior (load unpacked, capture a fixture page, assert
  payload), typescript-lsp for implementation, vitest for extraction units; ≥90% new code.
- **`security-review` mandatory** on the bridge + permissions (17.1, 17.5).
- **Extension is minimal-permission**: manifest requests only `activeTab` + the explicit
  capture action; no broad host permissions.

## Plugins (per `docs/07`)

`chrome-devtools-mcp` (extension debugging) · `playwright` (extension testing) · `frontend-design`
(extension UX, 17.5) · `typescript-lsp` (implementation).

## Build / packaging notes

- **New top-level `extension/` workspace** (Q7) — separate from the Tauri/Vite frontend build.
  MV3 manifest + `webextension-polyfill` → single source builds both Chrome and Firefox.
- **No web-store publish** (Q9) — the extension is installed via the ACOS install wizard
  (optional toggle); sideloaded/unpacked. Manual updates accepted for alpha.

## Deferred (recorded, not dropped)

| Item | Why deferred | Reopen when |
|------|--------------|-------------|
| Site-specific parsers (LinkedIn/Indeed/Greenhouse DOM scrapers) | Generic readability + local-LLM fallback covers any page (Q8); per-site scrapers are maintenance debt | a high-volume site needs precision → add one parser behind the same interface |
| Direct ATS / job-board API integrations | Capture is page-based + local-first; API integrations are outbound + per-vendor | v2 ecosystem (`docs/v2/ROADMAP.md`) |
| Chrome Web Store / AMO listing | Alpha installs via wizard (Q9); store review adds lead time | public beta / wider distribution |
| Cloud sync of captured jobs | Local-first (ADR-001); bridge is localhost-only | multi-device sync opt-in → own ADR |

## Token-efficiency ("Both")

- **Dev-time:** RTK · caveman+ponytail · ONE `context7` batch (MV3 manifest v3, webextension-
  polyfill, Tauri sidecar port) · bounded read pass.
- **Runtime:** extraction prefers **heuristic readability** (free) and only escalates to the
  **local LLM** when heuristics fail (Q8) — no LLM call on the common case; capture is
  user-triggered, so zero idle cost.
