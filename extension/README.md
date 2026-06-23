# ACOS Job Capture — Browser Extension (Phase 17, ADR-019)

Captures a job posting from the current page into the local ACOS backend. Local-first,
explicit-click only, no tracking.

## Build (single source → Chrome + Firefox)

```bash
cd extension
npm install
npm run build      # → dist/chrome/ and dist/firefox/
npm test           # extraction + manifest-permission checks (node --test, no deps)
```

## Install (sideload — no web store, ADR-019 Q9)

- **Chrome:** `chrome://extensions` → Developer mode → Load unpacked → `dist/chrome`.
- **Firefox:** `about:debugging` → This Firefox → Load Temporary Add-on → `dist/firefox/manifest.json`.

## Pair (one-time, ADR-019 §1)

1. Open ACOS → **Settings → Browser extension** → *Generate pairing token*.
2. Paste the token into the extension popup → **Pair**.

The token is presented on every request; the backend rejects unpaired requests
(default-closed). The bridge is **app-gated** — it only works while ACOS is running;
otherwise the capture is queued until you reopen ACOS.

## Capture

Click the extension, then **Capture this job**. It extracts title / company /
responsibilities / qualifications from the active tab, screens the text through the
ADR-017 injection defense, and creates an **application draft** you review in ACOS —
nothing is submitted anywhere (ADR-012).

## Security / privacy (the strict rules)

- Manifest requests only `activeTab` + `scripting` + `storage` — **no** history, tabs,
  cookies, webRequest, or broad host permissions (enforced by `test/extract.test.mjs`).
- The content script runs **only** on an explicit click — no background reads, no
  auto-capture.
- Loopback-only bridge, origin + one-time-token gated.
