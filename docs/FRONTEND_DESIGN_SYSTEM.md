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

## 6. Verification
`npm run test` (vitest: motion + transient logic, 200ms gate, prefetch dedup,
velocity clamp) · `npm run build` (tsc gate + bundle report) · `npx playwright test`
(e2e + `perf-1106` trace). Capture FPS via the 11.0 overlay (`?perf=1` or ⌘⇧P in
dev). Record bundle/FPS deltas in `docs/PERFORMANCE_LOG.md`.

> ⚠️ RTK can serve a stale cached "No tests found" for filtered Playwright runs.
> For a truthful run use the binary directly: `./node_modules/.bin/playwright test <spec>`.
