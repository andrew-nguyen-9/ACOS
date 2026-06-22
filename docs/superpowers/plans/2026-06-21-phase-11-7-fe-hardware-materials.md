# Phase 11.7 — Frontend Hardware-Accelerated Materials (WebGL)

**Track:** Frontend · **Depends on:** 11.5, 11.6, 11.0 (FPS budget is the gate) · **Status:** Planned

> Read the roadmap index first. **First heavy tier.** Hard rule: if a WebGL material can't hold
> 60fps (120 on ProMotion) it ships default-off behind a setting. The 11.0 FPS overlay is the judge.

---

## 1. Context

CSS `backdrop-filter` blur (still partly present) is expensive during motion (PERF-AC-002). 11.7
moves premium materials — animated gradient/noise backgrounds, glass, specular highlights — onto a
WebGL canvas via `@react-three/fiber`, where shaders run on the GPU compositor at high frame rates.
It also adds App-Nap throttling so the canvas costs ~0 when the window is hidden/blurred.

**CSP note (important):** `src-tauri/tauri.conf.json` has `script-src 'self'`. `three`/R3F do **not**
require `eval`/`wasm-unsafe-eval` for normal use, so WebGL is allowed. If a future shader uses a Web
Worker or `Blob:` URL, add `worker-src 'self' blob:` to CSP — check during impl and update the CSP
+ note it in `docs/TROUBLESHOOTING.md`.

## 2. Guidelines implemented (IDs)

- **HAM-001** WebGL/shader-based materials · **HAM-002** dynamic specular highlights (mouse-mapped)
- **PERF-AC-002** material proxy / GPU offload (complete the migration started in 11.5)
  · **PERF-AC-003** will-change discipline around canvas-adjacent DOM
- **DMI-003** App Nap & background throttling (Page Visibility + Tauri focus → pause RAF/WebGL)
- Catalog: #82 sub-pixel shimmer (now real, shader-driven), #90 ambient focus glow

## 3. Goals

- A single **WebGL background layer** (`<MaterialCanvas>`) behind the app shell: animated
  gradient + subtle noise, custom light-refraction, P3-aware. One canvas, not per-component (HAM-001).
- **Dynamic specular highlights** on primary cards/buttons: cursor position (from the 11.5 transient
  store, **no React state**) drives a radial highlight / normal-map response (HAM-002).
- **App-Nap throttling**: a global RAF/clock that pauses on `visibilitychange` hidden and on Tauri
  window blur; resumes on focus (DMI-003). All animation loops subscribe to it.
- **Graceful degradation**: a capability check (WebGL available? reduced-motion? low-power?) and a
  Settings toggle; when off, fall back to the cheap static proxy from 11.5. Never required for function.

## 4. Non-goals (YAGNI)

- No per-component WebGL canvases (one shared canvas only — multiple contexts kill perf).
- No 3D models/scenes — this is 2D-ish full-screen shader material, not a 3D world.
- No gyro/normal-map from device sensors (cursor only).
- No physics in shaders. No post-processing stack.

## 5. Design

- Install `three` + `@react-three/fiber`. Lazy-load the whole canvas module (`React.lazy` +
  intent/idle) so it's **not** in the initial bundle (PERF-IL-001) — TTI stays fast.
- `frontend/src/webgl/MaterialCanvas.tsx`: a fixed, pointer-events-none full-screen `<Canvas>`
  rendering a fragment-shader plane. Uniforms: time (from the throttled clock), pointer (from
  transient store), resolution, P3 accent. `frameloop="demand"` or capped DPR to bound cost.
- `frontend/src/webgl/shaders/material.frag.glsl` (+ `.vert`): gradient + value noise + soft
  refraction. Keep it cheap; profile on 5K display.
- `frontend/src/webgl/useSpecular.ts`: maps transient pointer → CSS custom props on a card
  (`--spec-x/--spec-y`) driving a CSS radial-gradient highlight — **CSS does the per-card highlight**,
  shader does the background. (Cheaper than a canvas per card; honors HAM-002 without context sprawl.)
- `frontend/src/webgl/clock.ts`: singleton animation clock; `pause()/resume()` wired to
  `document.visibilitychange` and Tauri `appWindow.onFocusChanged` (DMI-003). Every loop (here +
  11.6 scroll loops + 11.9 particles) uses it.
- `frontend/src/lib/capability.ts`: `supportsWebGL()`, `prefersReducedMotion()`, returns an
  effort tier. Settings page gets a "Visual effects: Full / Reduced / Off" control persisted to
  backend `system_config` (or local storage).
- Replace remaining `backdrop-blur` in `AppShell` with the canvas material + thin CSS glass.

## 6. File-level plan

```
NEW  frontend/src/webgl/MaterialCanvas.tsx
NEW  frontend/src/webgl/shaders/material.frag.glsl
NEW  frontend/src/webgl/shaders/material.vert.glsl
NEW  frontend/src/webgl/useSpecular.ts
NEW  frontend/src/webgl/clock.ts
NEW  frontend/src/lib/capability.ts
EDIT frontend/src/App.tsx / AppShell.tsx        (mount lazy MaterialCanvas behind shell; remove live blur)
EDIT frontend/src/pages/SettingsPage.tsx        (visual-effects tier control)
EDIT frontend/src-tauri/tauri.conf.json         (CSP worker-src/blob ONLY if shaders need it)
EDIT frontend/vite.config.ts                     (glsl import support if needed, e.g. vite-plugin-glsl)
EDIT frontend/package.json                        (three, @react-three/fiber, [vite-plugin-glsl])
EDIT docs/TROUBLESHOOTING.md                      (WebGL/CSP notes, how to disable effects)
```

## 7. Test plan

- Unit: `capability.ts` returns Off under reduced-motion / no-WebGL; `clock` pauses on hidden.
- Playwright e2e: app renders with canvas present (full tier) and with effects Off (canvas absent),
  no console/WebGL errors in either; Settings toggle persists.
- **Manual perf gate (BLOCKING):** 11.0 overlay must show ≥60fps idle with the canvas active on the
  target Mac; long-tasks 0 during nav. Capture a DevTools performance trace + a `take_screenshot`.
  If it can't hold 60, default the tier to Reduced/Off and document. Attach evidence to PR.

## 8. Plugin orchestration checklist

- [ ] `context7` — `@react-three/fiber` (frameloop, DPR), three.js shader material, vite glsl plugin, Tauri v2 window focus API.
- [ ] `chrome-devtools` skill — FPS + GPU profiling for the perf gate.
- [ ] `frontend-design` — shader aesthetic (must look intentional, not a screensaver).
- [ ] `security-guidance` — review any CSP change (loosening script/worker-src is security-relevant).
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

This is the **budget-spending** segment. Bounds: one canvas, capped DPR (e.g., ≤2), `frameloop`
demand-or-throttled, paused when hidden (DMI-003). three+R3F (~150KB gz) must be **lazy** so initial
bundle is unaffected (PERF-IL-001). Must pass the BLOCKING 60fps gate or ship default-off.

## 10. Risks & mitigations

- *5K display fill-rate cost* → cap DPR, lower-res render target upscaled, cheap shader; measure.
- *WebGL context loss / older GPUs* → capability check + static fallback; handle `webglcontextlost`.
- *CSP breakage* → test production Tauri build, not just `vite dev`; adjust CSP minimally.
- *Battery drain* → App-Nap throttling is mandatory, not optional, in this segment.

## 11. Definition of Done

Single lazy WebGL material canvas with P3 + specular, cursor-driven via transient store (no
re-renders), App-Nap throttling on hidden/blur, capability-based degradation + Settings tier, live
blur removed. BLOCKING 60fps gate passed (or default-off documented). e2e green, bundle initial-load
unchanged, evidence attached.
