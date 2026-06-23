# Phase 11.8 — Deep macOS Integration + Signature Features

**Track:** Frontend (+ Rust/Tauri) · **Depends on:** 11.5–11.7 · **Status:** Planned

> Read the roadmap index first. This segment touches the Rust side (Tauri plugin) and the IPC
> bridge. Performance rule for IPC: never spam the bridge — throttle/batch (PERF-IPC-001).

---

## 1. Context

The app now has tokens, kinematics, and WebGL materials. 11.8 makes it feel *native* (theme-synced
transitions, real haptics, instant local assets) and lands the first two **signature product
features** that differentiate a career copilot from a generic CRUD app.

Current facts:
- Tauri v2; `src-tauri/tauri.conf.json` has one window, CSP locked to `connect-src localhost:8000`.
- No custom Rust plugins yet; backend is a sidecar (`externalBin acos-backend`).
- Copilot UI exists (`components/copilot/`, `pages/CopilotPage.tsx`, `services/copilot.ts`).
- Resume UI exists (`pages/ResumePage.tsx`, `components/resume/`).

## 2. Guidelines implemented (IDs)

- **DMI-001** system theme synchronization (clip-path reveal from cursor)
- **DMI-002** Touchbar & haptic integration (native haptics via Rust plugin)
- **PERF-IPC-001** IPC payload throttling/batching · **PERF-IPC-002** custom-protocol asset serving
- Feature **RCL-002** X-Ray Impact Mapping (ATS/metric overlay on resume bullets)
- Feature **COP-003** Ghost-Writing Ink Trail (copilot ghost text, Tab to accept)
- Catalog: #14 haptic pagination, #84 haptic command-palette ticks, #35 redaction mask (if cheap)

## 3. Goals

### macOS integration
- **Theme sync**: listen to Tauri theme change events; animate light/dark swap as a circular
  `clip-path` reveal originating from the cursor (DMI-001), reduced-motion → instant.
- **Native haptics**: a small Rust Tauri plugin exposing `haptic(pattern)` (uses macOS
  `NSHapticFeedbackPerformer`); invoked on destructive confirms, successful generation, drag-drop
  settle (DMI-002). No-op on non-mac.
- **Custom-protocol assets**: register a `asset://` URI scheme in Rust to serve local images/
  exported PDFs/heavy JSON via memory-mapped reads instead of HTTP (PERF-IPC-002).
- **IPC discipline**: any high-frequency Tauri invoke (window resize, drag) is debounced via a
  16ms/RAF batcher (PERF-IPC-001).

### Signature features
- **X-Ray Impact Mapping (RCL-002)**: hovering a resume bullet reveals a glass overlay showing its
  structural math — action verb, quantified metric presence, ATS keyword coverage, confidence level.
  Data comes from existing backend scorers (`bullet_scorer`, `ats/scorer`, evidence confidence).
- **Ghost-Writing Ink Trail (COP-003)**: copilot suggestions render as faint ghost text after the
  cursor; `Tab` accepts with an ink-bleed animation; `Esc` dismisses. Streams from copilot service.

## 4. Non-goals (YAGNI)

- No Touchbar UI (deprecated hardware) — keep haptics only despite the guideline title.
- No spatial audio / interview sim (that's 11.9).
- No new backend scoring — X-Ray *visualizes* existing scores; if a datum is missing, hide it.
- Redaction mask only if it's a trivial CSS blur toggle; otherwise drop.

## 5. Design

### Rust / Tauri
- `src-tauri/src/haptics.rs`: a command `haptic(pattern: String)` calling macOS haptic API via
  `objc2`/`cocoa` (or a maintained crate); `#[cfg(target_os="macos")]`, no-op elsewhere. Register
  in `lib.rs`/`main.rs` invoke handler.
- `asset://` scheme via `register_uri_scheme_protocol` serving from an allowlisted dir (security:
  validate/normalize path, no traversal — `security-guidance`).
- Frontend `src/lib/haptics.ts`: `tap()/success()/warn()` wrappers (invoke, throttled, guarded).
- Frontend `src/lib/ipc.ts`: `batchedInvoke` using a RAF/16ms queue (PERF-IPC-001).

### Theme sync
- `src/hooks/useThemeReveal.ts`: subscribe to Tauri theme events; on change set a CSS
  `clip-path: circle()` animation centered at last cursor pos (from transient store), swap theme
  class at midpoint. Reduced-motion → instant class swap.

### X-Ray
- `src/components/resume/BulletXRay.tsx`: on bullet hover (intent-delayed), a glass popover (uses
  11.5 material) showing verb/metric/keyword/confidence chips from data already returned by the
  resume/ATS endpoints. Pointer-driven position via transient store (no re-render storm).

### Ghost text
- `src/components/copilot/GhostText.tsx` + `useGhostCompletion.ts`: render streamed suggestion as
  low-opacity inline text; `Tab` commits with ink-bleed (framer-motion clip/opacity), `Esc`
  dismisses. Hooks into existing `services/copilot.ts` streaming.

## 6. File-level plan

```
NEW  frontend/src-tauri/src/haptics.rs           (+ wire invoke handler in lib.rs/main.rs)
EDIT frontend/src-tauri/src/lib.rs|main.rs       (register haptic cmd + asset:// scheme)
EDIT frontend/src-tauri/tauri.conf.json          (asset protocol capability/permissions; csp img-src asset:)
EDIT frontend/src-tauri/Cargo.toml               (haptics crate dep)
NEW  frontend/src/lib/haptics.ts
NEW  frontend/src/lib/ipc.ts                      (batchedInvoke)
NEW  frontend/src/hooks/useThemeReveal.ts
NEW  frontend/src/components/resume/BulletXRay.tsx
NEW  frontend/src/components/copilot/GhostText.tsx
NEW  frontend/src/components/copilot/useGhostCompletion.ts
EDIT frontend/src/pages/ResumePage.tsx           (mount BulletXRay on bullets)
EDIT frontend/src/pages/CopilotPage.tsx          (ghost text in the editor)
EDIT frontend/src/App.tsx                         (useThemeReveal at root)
```

## 7. Test plan

- Rust: a unit test that `haptic("success")` returns Ok on mac, no-op Ok elsewhere; asset path
  validator rejects traversal (`../`).
- Frontend unit: `batchedInvoke` coalesces N calls in a frame into ≤1; ghost-completion Tab/Esc state.
- Playwright e2e: hover bullet → X-Ray popover shows expected chips; copilot ghost text appears and
  Tab accepts; theme toggle swaps without console errors.
- **Manual:** verify real haptic tick on Mac hardware; theme reveal at 60fps; X-Ray hover no jank.

## 8. Plugin orchestration checklist

- [ ] `context7` — Tauri v2 custom URI scheme, theme events, invoke handlers, capabilities/permissions; macOS haptics crate.
- [ ] `security-guidance` — **required**: asset:// path allowlist + traversal prevention; CSP changes for `img-src asset:`; review the new Rust surface.
- [ ] `pr-review-toolkit` — Rust + IPC is new attack surface; run reviewer.
- [ ] `frontend-design` — ghost text + X-Ray must feel refined.
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

`asset://` is **faster** than HTTP fetch for local files (PERF-IPC-002). `batchedInvoke` reduces IPC
load. Theme reveal + ink-bleed are transform/opacity/clip-path (compositor). X-Ray popover is a
single lazy element. No initial-bundle impact. Verify hover/animation FPS with 11.0 overlay.

## 10. Risks & mitigations

- *Native haptics crate churn* → isolate in `haptics.rs`; fall back to silent no-op if unavailable.
- *asset:// path traversal* → strict allowlist + canonicalize; covered by a Rust test.
- *Ghost text fights IME/controlled input* → render in an overlay layer, not in the textarea value.
- *Theme reveal clip-path repaint* → keep the revealed layer promoted; reduced-motion bypass.

## 11. Definition of Done

Native haptics plugin (mac, no-op elsewhere), asset:// serving with path validation, batched IPC,
theme clip-path reveal, X-Ray impact mapping on resume bullets, copilot ghost-text with Tab-accept —
all tested, security review of the Rust/CSP surface done, e2e green, FPS verified.
