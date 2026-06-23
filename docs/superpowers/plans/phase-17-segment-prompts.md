# Phase 17 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. **5 segments** (4 build + close-out).
Map + reconciliation: `phase-17-roadmap.md`. Phase ends at **17.5** — no .6+.

## Recommended order (dependency-correct)

```
17.1 extension scaffold + paired bridge (ADR-019)   FIRST — no capture leaves the browser until paired/app-gated
17.2 page capture + extraction                      ← 17.1   readability + local-LLM fallback; sanitize + injection screen
17.3 normalization + enrichment                     ← 17.2   surface existing normalizer + Phase-9 enrichment
17.4 one-click Add to ACOS → draft                  ← 17.3   ingestion route → Application draft; review-not-submit
17.5 UX + install-wizard + Firefox parity + close   ← 17.4
```

## Session-wide invariants (true for ALL — stated once)

- **Branch:** `feat/phase-17-browser-extension` (off `main`, Phase 16 merged). One commit/segment.
  **PR deferred to 17.5.** Git Attribution: NO Claude/Anthropic in commits/PRs/branches.
- **Rules (CLAUDE.md):** no hallucination + ADR-006; read `docs/` first; **`context7` for APIs**
  (MV3 manifest v3, `webextension-polyfill`, Tauri sidecar port, FastAPI CORS — never from memory).
  TDD: failing test FIRST, ≥90% new code, suite green. Ponytail: rung 1. Caveman: terse;
  code/security normal.
- **Phase-17 strict rules (assert, don't claim):** NO background tracking · NO browsing-history
  collection · NO unrelated page scraping · ONLY explicit user-triggered capture. Tests confirm the
  manifest requests no history/tab/cookie perms and the content script acts only on click.
- **Plugins:** `chrome-devtools-mcp` (debug) · `playwright` (test: load unpacked, capture fixture,
  assert payload) · `frontend-design` (UX, 17.5) · `typescript-lsp` (impl). `security-review` on
  17.1/17.5.
- **Carried boundaries:** captured content passes the **ADR-017 injection screen** (16.4) before
  touching ACOS; **ADR-012** — capture creates a *draft*, never submits; **ADR-019** — paired,
  localhost-only, app-gated bridge.
- **Token-efficiency:** RTK · ONE `context7` batch · bounded read pass. Extraction prefers
  heuristic readability (free), escalates to local LLM only on failure (Q8).
- **New top-level `extension/` workspace (Q7)** — separate from the Tauri/Vite frontend build; MV3
  + `webextension-polyfill` single source builds Chrome + Firefox. **No web-store publish (Q9)** —
  installed via the app wizard, sideloaded.
- **Shipped surface you build on (verify shapes — don't assume):**
  - **Job ingestion:** `backend/ingestion/jobs.py`, `normalizer.py`, `entity_extractor.py`,
    `routes/ingestion.py` (the receive-a-JD contract the extension calls).
  - **Application draft:** `backend/models/application.py` (`Application` + `status` draft),
    `routes/application.py`, `frontend/src/pages/ApplicationsPage.tsx`.
  - **Enrichment (Phase 9):** `services/strategy/role_fit_scorer.py`, `skill_gap_forecaster.py`;
    **ATS keywords:** `services/ats/`.
  - **Bridge security (16.1):** auth/session + `lib.rs` sidecar spawn (the sidecar the extension
    pairs to). **Injection screen (16.4):** the ingestion-time checkpoint.
  - **Install wizard:** `frontend/src/pages/FirstRunWizard.tsx`, `SettingsPage.tsx` (the optional
    "install extension / pairing token" toggle).

---

## 17.1 — Extension Scaffold + Paired Backend Bridge (ADR-019)

Implement Phase 17.1 — scaffold the `extension/` workspace (MV3 + webextension-polyfill, builds
Chrome + Firefox) and the **secure bridge**: one-time token pairing, localhost-only, origin-checked
CORS, app-gated. **ADR-019 FIRST** — no capture leaves the browser until this exists. Brief items
1 (scaffold) + 5 + 6 (security).

PRECONDITION: Phase 16 merged (auth + sidecar). No `extension/` exists yet.

Read first (STOP at the sidecar port + auth middleware + a route to add the bridge to): (1)
`phase-17-roadmap.md` + ADR-019 (drafted). (2) `frontend/src-tauri/src/lib.rs` (sidecar spawn —
the port the extension reaches; confirm it's loopback). (3) `backend/main.py` (CORS config + where
the pairing/bridge route mounts) + the 16.1 auth/session. (4) `context7`: MV3 manifest v3 +
webextension-polyfill build (single source → Chrome/Firefox).

Order: ratify ADR-019 → TDD (backend: unpaired request → **rejected** (default-closed); a paired
token → accepted; CORS allows only the extension origin; **app-closed → bridge unreachable** (no
always-on listener); extension: manifest requests **only** `activeTab` + the capture action, NO
history/tabs/cookies — a test asserts the permission set) → implement (`extension/` MV3 scaffold +
polyfill build; backend pairing endpoint generating a one-time token surfaced in the app; token
stored in the extension, presented per request) → `security-review` → verify (playwright: load
unpacked, pair, hit the bridge).

Traps: (1) **Default-closed** — unpaired/unknown-origin = rejected, never served. (2) **App-gated**
— the bridge lives only while the app runs; extension degrades to "queued, open ACOS." (3)
**Minimal perms** — `activeTab` only; a broad host-permission is the privacy bug the strict rules
forbid (test the manifest). (4) **Loopback only** — bind localhost; no remote host reaches it. (5)
ponytail: one workspace, polyfill builds both browsers — don't fork Chrome/Firefox sources.

Files: ratify ADR-019, NEW `extension/` (manifest, background, pairing client, build config), EDIT
`backend/main.py` (CORS + pairing route) + a pairing-token surface in the app, backend + playwright
tests. Def-of-done: `extension/` builds for Chrome + Firefox + paired localhost-only app-gated
bridge (unpaired rejected, minimal perms asserted) + `security-review` clean, commit.

---

## 17.2 — Page Capture + Extraction

Implement Phase 17.2 — the content script that, on explicit click, extracts the job posting
(title, company, responsibilities, qualifications) from the current page, sanitizes it, and runs it
through the injection screen. Brief item 1 (extraction) + 6. Hybrid extraction (Q8): heuristic
readability first, local-LLM fallback.

PRECONDITION: 17.1 (the paired bridge). Injection screen exists (16.4, ADR-017).

Read first (STOP at the bridge client + the ingestion-time injection screen): (1) ADR-017
(injection) + the 16.4 ingestion checkpoint. (2) the 17.1 bridge client (how the content script
sends a payload). (3) `context7`: a readability/DOM-extraction approach for content scripts. (4)
`backend/ingestion/jobs.py` (the target schema fields to extract toward).

Order: brainstorm (confirm: click → content script extracts via **heuristic readability** (headings/
sections → title/company/responsibilities/qualifications); on low-confidence extraction, **escalate
to the local LLM** through the backend; sanitize HTML→text; the payload then hits the ingestion-time
injection screen server-side) → ADR? skip (consumes ADR-019/017) → TDD (extraction on fixture pages
yields the four fields; sanitization strips scripts/markup; **capture fires only on explicit click**
— no auto/background capture (assert); low-confidence → LLM fallback path; injection-laced fixture is
screened) → implement → verify (playwright on fixture pages).

Traps: (1) **Explicit-only** — content script does nothing until the user clicks; no MutationObserver
auto-capture, no background reads (strict rule, tested). (2) **Heuristic first** — LLM only on
failure (Q8); don't call the model on every capture (cost/latency). (3) **Sanitize before send** —
strip scripts/markup; the server still runs the injection screen (defense in depth). (4) **Job-only**
— extract the posting, never the user's other tabs/history/cookies.

Files: NEW content-script extraction + sanitizer in `extension/`, EDIT the bridge payload, maybe a
thin backend LLM-fallback hook, vitest (extraction units) + playwright. Def-of-done: explicit-click
capture of the four fields + readability-with-LLM-fallback + sanitized + injection-screened +
explicit-only asserted, commit.

---

## 17.3 — Job Normalization + Enrichment

Implement Phase 17.3 — map the captured payload to ACOS's standard job schema via the **existing**
normalizer, and surface existing enrichment (inferred industry, skill graph, seniority, ATS
keywords). Brief items 2 + 4. **Surface, don't rebuild.**

PRECONDITION: 17.2 (a captured, screened payload). Normalizer + enrichment engines exist.

Read first (STOP at the normalizer + enrichment contracts): (1) `backend/ingestion/normalizer.py`
+ `entity_extractor.py` + `jobs.py` (the standard schema + skill extraction). (2) Phase-9
`role_fit_scorer.py` / `skill_gap_forecaster.py` (seniority/skill-graph signals) + `services/ats/`
(ATS keyword extraction). (3) confirm the captured shape from 17.2 maps cleanly.

Order: brainstorm (confirm: captured payload → normalizer → standard schema → existing enrichment
(industry/skill-graph/seniority/ATS-keywords), each confidence-tagged per ADR-006) → ADR? skip →
TDD (a captured fixture normalizes to the canonical schema; enrichment fields populate from the
existing engines; thin/ambiguous capture → `weak_inference`, not fabricated) → implement (wire
capture→normalizer→enrichment; no new engine) → verify.

Traps: (1) **Reuse the normalizer** — don't write a second one for extension input (ponytail). (2)
**Honest enrichment** — industry/seniority are inferred → confidence-tagged; thin input → labeled
low, never invented (ADR-006). (3) **ATS-ready** — keyword extraction reuses `services/ats/`. (4)
captured input is just another ingestion source — it flows the same path as a pasted JD.

Files: EDIT `ingestion/jobs.py`/`normalizer.py` wiring only if the capture shape needs a thin
adapter, surface enrichment via existing services, tests. Def-of-done: captured job → standard
schema + enrichment (industry/skill-graph/seniority/ATS-keywords) confidence-tagged via existing
engines, no new engine, suites green, commit.

---

## 17.4 — One-Click "Add to ACOS" → Application Draft

Implement Phase 17.4 — the one-click flow: capture → ingestion route → auto-create an **application
draft** the user reviews. Brief item 3. **Review-not-submit (ADR-012).**

PRECONDITION: 17.3 (normalized+enriched job). `routes/ingestion.py` + `Application` draft +
`ApplicationsPage` exist.

Read first (STOP at the ingestion route + the draft create path): (1) `routes/ingestion.py` (the
receive endpoint) + `routes/application.py` (`Application` draft create + `status`). (2)
`ApplicationsPage.tsx` (where the new draft appears) + ADR-012 (no-submit). (3) the 17.1 bridge
(the call the extension makes).

Order: brainstorm (confirm: extension "Add to ACOS" → bridge → ingestion route → create an
`Application` in `draft` status with the normalized+enriched job; the user opens ACOS and sees the
draft to review/tailor; **nothing is submitted anywhere**) → ADR? skip (consumes ADR-012/019) → TDD
(add-to-ACOS creates exactly one draft with the captured fields; **no external submit path exists**
on the flow (assert, mirror 15.x); duplicate capture is de-duped or flagged, not double-created) →
implement → verify (playwright end-to-end: capture → draft appears).

Traps: (1) **Draft only** — `status=draft`; the user reviews; no auto-apply (ADR-012, tested). (2)
**Idempotent-ish** — re-capturing the same posting shouldn't silently create duplicates; de-dupe or
flag. (3) **Reuse the CRM** — the draft is a normal `Application`; don't fork a parallel entity. (4)
app-gated — if the app is closed, the capture queues (17.1) and syncs on open.

Files: EDIT `routes/ingestion.py`/`application.py` (thin draft-create from capture if not already),
EDIT extension "Add" action + `ApplicationsPage` (surface the new draft / queued state), backend +
playwright tests. Def-of-done: one-click capture → reviewable application draft + no-submit path
(asserted) + de-dupe + queued-when-app-closed, suites green, commit.

---

## 17.5 — Extension UX + Install-Wizard Integration + Firefox Parity + Close-out

Run Phase 17.5 — polish the extension UX (`frontend-design`), integrate install + pairing into the
app wizard, confirm Firefox parity, then verification + docs + ADR ratification → merge. Brief
item 1 (Firefox) + the install flow.

PRECONDITION: 17.1–17.4 shipped. First action: enumerate shipped + deferred (site-specific parsers,
ATS APIs, web-store listing, cloud sync).

Read first (STOP at the wizard + the extension build): (1) `phase-17-roadmap.md` (reconciliation +
deferred). (2) `FirstRunWizard.tsx` / `SettingsPage.tsx` (where the optional "install extension +
pairing token" toggle lives — Q9). (3) the `extension/` build (confirm the Firefox target builds
from the same source).

Order: a checklist. (1) **UX** (`frontend-design`): capture button states, success/queued feedback,
pairing flow — minimal, on-brand. (2) **Install integration**: the wizard offers the extension as an
**optional** step with the pairing token (Q9 — sideload, no web store). (3) **Firefox parity**:
build + load the Firefox target; capture works; assert the polyfill single-source holds. (4)
**Security**: `security-review` on the bridge + permissions + capture (no over-permission, no
background tracking — the strict rules, test-backed). (5) **Docs**: `USER_GUIDE` (install + capture),
`ARCHITECTURE_OVERVIEW`, `08_ROADMAP`, `INDEX`. (6) **ADR**: ratify ADR-019.

Traps: (1) **verification-before-completion** — Firefox parity *demonstrated* (built + captured),
not assumed. (2) **Optional install** — never forced; the app works without the extension. (3)
**Strict-rules audit** — the manifest + content script reconfirmed: explicit-only, minimal perms,
no history/tracking. (4) close out only what shipped; deferrals (parsers/APIs/store) documented.

Plugins: `frontend-design`, `playwright`, `chrome-devtools-mcp`, `security-review`, `pr-review-
toolkit`, `claude-md-management`. Files: extension UX, wizard/Settings integration, Firefox build
config, docs, ADR-019 ratification. Def-of-done: polished capture UX + optional wizard install +
Firefox parity demonstrated + security audit clean + docs + ADR-019 ratified → **Phase 17 ready to
merge to `main`** (PR opens here).
