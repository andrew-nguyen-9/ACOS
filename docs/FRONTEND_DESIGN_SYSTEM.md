# ACOS Frontend Design System (Phase 11.5)

The perf-positive foundation for the frontend revamp (11.6–11.9 build on it). The
identity is **macOS-native dark glass**: true-black canvas, frosted translucent
panels, a single blue accent, Apple system confidence colors. Everything here is
hardware-accelerated and performance-gated — *performance is never traded for show*
(see `docs/PERFORMANCE_LOG.md`).

## 1. Tokens — `src/styles/tokens.css`

Single source of truth for color, material, motion, and type. Tailwind reads these
vars (`tailwind.config.js`) so utilities stay in sync.

### Color
- **Two representations per accent/confidence color:**
  - `--accent-rgb: 76 141 255` — sRGB channels, consumed by Tailwind as
    `rgb(var(--accent-rgb) / <alpha-value>)`. This is why `bg-accent/10`,
    `text-accent`, `border-verified/20` etc. work with opacity modifiers.
  - `--accent` (full color) — widened to **Display-P3** on capable screens via
    `@supports (color: color(display-p3 …))` (HAM-003), with the sRGB value as the
    fallback. Used directly by hand-authored signature surfaces (the AppShell
    aurora, accent glows) where the wider gamut is the point.
- **Why the split:** Tailwind v3's `<alpha-value>` mechanism needs channel-based
  colors; P3 `color()` can't compose with it. Rather than lose opacity modifiers
  *or* lose P3, we keep both and use each where it fits. New P3-in-utility needs
  (e.g. `.text-accent-p3`) can be added as utilities later — YAGNI for 11.5.
- Confidence colors map to the three-level system (`docs/adr/ADR-006`): `verified`
  (green), `strong` (cyan), `weak` (orange).
- Base: `--bg: #0a0a0a` (true-dark luminance, catalog #5), `--fg`, `--fg-muted`.

### Material / elevation
`--glass-bg` (translucent panel fill), `--glass-border`, `--elevation-card`
(→ `shadow-card`), `--elevation-panel` (→ `shadow-panel`).

### Motion
`--ease-standard` / `--ease-out` (→ `ease-standard` / `ease-out-expo`),
`--duration-fast|base|slow` (→ `duration-fast` etc.). Collapsed to `0ms` under
`prefers-reduced-motion`.

### Typography
- `--font-sans` / `--font-display` → Tailwind `font-sans` / `font-display`. System
  **SF Pro** on macOS (`-apple-system`/`BlinkMacSystemFont`), **Inter** fallback
  cross-platform (no custom font hosting — CSP- and ADR-005-aligned). VPT-001.
- `--fs-display`: fluid `clamp()` display size. Line-heights stay on the **4px
  baseline grid** (VPT-002); Tailwind's default spacing scale *is* that grid.
- **Numerics:** use `tabular-nums` (built-in Tailwind utility) for aligned data /
  metrics (VPT-003); `proportional-nums` for prose. See the Dashboard stats.

## 2. Motion primitives — `src/motion/index.ts`

**Everything that animates imports from here** so easing/springs aren't re-derived
and reduced-motion is uniform.
- `springs.gentle` / `springs.snappy` — physics-based transitions (no fixed
  duration). Panels use `gentle`; small/feedback UI uses `snappy`.
- Variants: `fadeUp`, `scaleIn`, `staggerContainer`. **OMTA only** — they animate
  `transform`/`opacity`, never layout-thrashing properties (PERF-AC-001).
- `flattenVariants(v)` — pure, unit-tested: strips transform props, keeps opacity,
  makes transitions instant. `prefersReducedMotion()` — matchMedia guard.
- **Global reduced-motion:** the app is wrapped in
  `<MotionConfig reducedMotion="user">` (App.tsx), so framer drops transform/layout
  animation and keeps opacity automatically; `flattenVariants` covers any
  hand-applied variants.

### framer-motion bundle discipline
Use the **`m` component** (not `motion.*`) under `<LazyMotion strict>`. Features
load **async** (`src/motion/features.ts`), so the feature set is code-split out of
the entry chunk. As of 11.6 the export is **`domMax`** (= `domAnimation` + drag +
layout projection), needed for velocity-dismiss (KMP-001) and `LayoutGroup`/
`layoutId` (KMP-003). It's ~28 kB gz but lives in the off-entry `features-*.js`
chunk; the entry chunk is unaffected. Don't import `motion.*` — strict mode throws.

## 3. Performance architecture

| Concern | Tool | Guideline |
|---------|------|-----------|
| High-freq input (mouse/scroll/drag) | `src/stores/useTransientInput.ts` — vanilla zustand store + in-place `live` object. `setPointer` updates a ref and notifies imperative `subscribe` listeners but **never re-renders**. | PERF-RP-001 |
| CSS containment | `.contain-paint` (`contain: layout paint`), `.contain-strict` utilities | PERF-RP-002 |
| Compositor promotion | `src/hooks/useWillChange.ts` — promote `will-change` on intent, release on settle (a permanent layer wastes GPU memory) | PERF-AC-003 |
| Material proxy | AppShell static pre-blurred aurora instead of live `backdrop-filter` | PERF-AC-002 |
| Code-split on intent | `src/components/ui/lazyOnIntent.tsx` + `src/routes.tsx` — sidebar warms a route's chunk on hover/focus | PERF-IL-001 |

**Never** route high-frequency input through `useState`. **Never** animate width/
height/top/left — use transform/opacity.

## 4. Reference implementations
- `src/layouts/AppShell.tsx` — material proxy, token glass, hover-prefetch nav.
- `src/pages/Dashboard.tsx` — staggered `fadeUp`/`scaleIn` entrance, token colors,
  `tabular-nums` stats, `font-display` heading. **Copy this page's patterns** when
  adopting the system elsewhere; remaining pages migrate incrementally.

## 5. Kinematics + state perception (Phase 11.6)

Physics motion + perceived-latency masking, all **OMTA (transform/opacity only)**.
Build on these; don't re-derive them.

| Primitive | File | Guideline | Notes |
|---|---|---|---|
| Velocity-dismiss | `src/hooks/useVelocityDismiss.ts` | KMP-001 | Drag a surface; `info.velocity` on `onDragEnd` feeds the exit spring (clamped). Pure `shouldDismiss`/`dismissTransition` are unit-tested. Applied to the Applications add-modal. |
| Scroll kinematics | `src/hooks/useScrollKinematics.ts` | KMP-002 | Thin `useScroll`+`useTransform` wrapper bound to a scroll container ref → collapsing header + scroll progress (`scaleX`). Positional collapse drops to constant under reduced-motion. |
| Layout projection | `<LayoutGroup>` in `App.tsx` + `layoutId` | KMP-003 | Shared-element list→detail. **Only on small, non-virtualized elements** (LearningPage ranking → detail). **Never put `layoutId` on virtualized rows** — transform-scroll re-renders make framer re-measure every frame → jank. |
| Predictive prefetch | `src/services/prefetch.ts` | ASP-001 | `warmRoute(path)` = chunk prefetch + `warm(endpoint)` fire-and-forget GET. Deduped, idempotent GET only, capped at 4 concurrent, skipped when `document.visibilityState==="hidden"`. Wired to nav hover/focus. |
| Perceptual load masking | `src/hooks/useDeferredLoading.ts` + `src/components/ui/Skeleton.tsx` | ASP-002 | 200ms gate: <200ms → nothing; >200ms → a skeleton that mirrors the real DOM dims (CLS=0). Replaces the spinner `PageFallback`. |
| Concurrent filtering | React `useTransition` | ASP-003 | List search/filter recompute wrapped in `startTransition`; the controlled input stays responsive. |
| Virtualization | `src/components/ui/VirtualList.tsx` | PERF-RP-003 | `@tanstack/react-virtual` + `content-visibility:auto`. Rows absolutely positioned via `translateY`. Parent owns the scroll ref so it also drives `useScrollKinematics`. **Adopt for lists >50 items** (ApplicationsPage). Small lists (LearningPage rankings) stay plain — virtualizing them is pure overhead. |

Measured: 500-row scroll = **0 long tasks, 60fps, 16 DOM rows**; modal fling = 0 long
tasks (`e2e/perf-1106.spec.ts`). Reference page: `src/pages/ApplicationsPage.tsx`
composes virtualization + scroll kinematics + `startTransition` + velocity-dismiss.

## 6. WebGL materials + App-Nap + capability tier (Phase 11.7)

One GPU-composited shader material behind the shell — **the first heavy tier, default-on
only while it holds 60fps**. Build 11.8/11.9 (haptics, particles) on the clock +
capability + canvas primitives below; **never add a second GL context.**

| Primitive | File | Guideline | Notes |
|---|---|---|---|
| Material canvas | `src/webgl/MaterialCanvas.tsx` + `shaders.ts` | HAM-001 / PERF-AC-002 | **One** full-screen R3F `<Canvas frameloop="demand">`, `pointer-events-none`, behind the shell. Fragment shader = gradient + value-noise + cursor focus-glow; uniforms `uTime`/`uPointer`/`uResolution`/`uAccent` fed from the P3 `--accent-rgb` token. DPR capped (Full ≤2, Reduced 1). Statically imports `three`; loaded only via `React.lazy` → never in entry. |
| App-Nap clock | `src/webgl/clock.ts` | DMI-003 | **The single pause/resume authority.** `subscribe(cb)` drives one shared rAF with continuous elapsed-seconds; parks on `visibilitychange` hidden + Tauri `onFocusChanged` blur → hidden window costs ~0. Every loop subscribes here — don't start private rAFs. Pause/resume unit-tested. |
| Capability tier | `src/lib/capability.ts` | — | `pickTier({pref,webgl,reducedMotion})` (pure, unit-tested) clamps the saved preference to `off` under no-WebGL or OS reduced-motion. Preference persisted to **localStorage** (`acos:visual-effects`, default `full`) — no backend round-trip. `Off` = the static §3 aurora. |
| Cursor specular | `src/webgl/useSpecular.ts` + `.specular-surface` CSS | HAM-002 | Transient pointer → `--spec-x/--spec-y` on a card; a **CSS** `radial-gradient` does the per-card highlight (no GL context per card). Opt in via `<GlassCard specular>`. Fires on pointer movement only; reduced-motion drops it. |
| Tier shim | `src/webgl/MaterialBackground.tsx` | PERF-IL-001 | Tiny, `three`-free entry component AppShell mounts. Resolves the tier, lazy-loads the canvas when on, owns the single `pointermove → setPointer` writer, re-resolves live on the Settings toggle (`acos:effects-changed`) + reduced-motion change. |

Settings → **Visual Effects: Full / Reduced / Off** (`SettingsPage.tsx`) writes the
preference + dispatches `acos:effects-changed` so the material re-tiers without reload.
Degradation is first-class: the app renders fully on `Off` via the cheap aurora, and
`webglcontextlost` unmounts the canvas to that same fallback. Measured: **60fps idle +
0 long-tasks on client nav** with the canvas active; entry chunk +0.91 kB gz (three is
off-entry). **CSP unchanged** — this material needs no `eval`/`wasm`/worker/blob.

## 7. macOS integration + signature features (Phase 11.8)

The first segment to cross the **Rust/Tauri boundary**. Native feel (theme sync, haptics,
local assets) + two signature product features. Build later segments on these primitives;
**never spam the IPC bridge** — high-frequency invokes must batch.

| Primitive | File | Guideline | Notes |
|---|---|---|---|
| Native haptics | `src-tauri/src/haptics.rs` + `src/lib/haptics.ts` | DMI-002 | Rust `#[command] haptic(pattern)` → macOS `NSHapticFeedbackManager` (`objc2-app-kit`, `#[cfg(target_os="macos")]`, no-op + `Ok` elsewhere). FE wrappers `tap()/success()/warn()` are **throttled (60ms) and guarded** (`isTauri()` — silent no-op in vite dev / e2e). Wired to resume/copilot success+error and ghost-accept. Haptics are **additive — never required for function**, so every call is best-effort. |
| asset:// scheme | `src-tauri/src/lib.rs` (`register_uri_scheme_protocol`) + `resolve_asset_path` | PERF-IPC-002 | Serves local files (images / exported docs) from the **allowlisted app-data dir** via memory read instead of HTTP. **Security chokepoint:** `resolve_asset_path` rejects `..` syntactically *and* `canonicalize`+`starts_with`-contains (symlink-safe); default-closed (403/404). CSP adds **only** `img-src 'self' asset:`. Unit-tested (`cargo test`). |
| IPC batching | `src/lib/ipc.ts` (`batchedInvoke` / `createBatchedInvoke`) | PERF-IPC-001 | rAF-coalesced invoker: N calls/frame per command collapse to **one** (last payload wins). Route any high-freq invoke (resize/drag) through it. Pure core (injected invoke + scheduler) is unit-tested. |
| Theme reveal | `src/hooks/useThemeReveal.ts` + `:root[data-theme="light"]` tokens | DMI-001 | OS theme change (`matchMedia` web / Tauri `onThemeChanged` prod) → circular **`clip-path` reveal** from the last cursor pos (transient store), swapping the `data-theme` class once the incoming-bg overlay covers. **Reduced-motion → instant swap, no overlay.** Default = absence of the attribute = the §1 true-dark; light is a **token-layer** flip (component-level light polish deferred). |
| X-Ray Impact Mapping | `src/components/resume/BulletXRay.tsx` | RCL-002 | Intent-delayed (260ms) hover on a resume bullet → glass popover (token glass) showing **action verb / quantified-metric / ATS-keyword coverage / confidence** — all derived from data the resume+ATS endpoints already return (**no new backend scoring**; a missing datum hides its chip). Portaled to `<body>`; position tracks the cursor **imperatively from the transient store** (no re-render storm). |
| Ghost-Writing Ink Trail | `src/components/copilot/{GhostText,useGhostCompletion}.tsx` | COP-003 | Copilot suggestion renders as faint accent **ghost text in an overlay layer** (never the input value — avoids IME/controlled-input fights). `Tab` accepts (ink-bleed: clip-path L→R reveal), `Esc` dismisses + suppresses until the next keystroke. State machine (`ghostReducer`) unit-tested; reduced-motion shows the ghost instantly. |

The **Rust invoke surface now exists** (`generate_handler![haptics::haptic]`) — it was
empty before 11.8. Any new command goes through `security-review` (real native attack
surface). Native haptics + asset:// **only exist in the packaged Tauri app** — browser
e2e can't exercise them; they're covered by `cargo test` + the honest manual-hardware check.

## 8. Verification
`npm run test` (vitest: motion + transient logic, 200ms gate, prefetch dedup,
velocity clamp, capability tier + clock pause/resume, **batchedInvoke coalescing + ghost
Tab/Esc state**) · `npm run build` (tsc gate + bundle report) · `cargo test` in
`src-tauri` (**haptic no-op contract + asset path validator**) · `npx playwright test`
(e2e + `perf-1106`/`materials-1107`/`macos-1108` traces). Capture FPS via the 11.0
overlay (`?perf=1` or ⌘⇧P in dev). Record bundle/FPS deltas in `docs/PERFORMANCE_LOG.md`.

> ⚠️ RTK can serve a stale cached "No tests found" for filtered Playwright runs.
> For a truthful run use the binary directly: `./node_modules/.bin/playwright test <spec>`.
