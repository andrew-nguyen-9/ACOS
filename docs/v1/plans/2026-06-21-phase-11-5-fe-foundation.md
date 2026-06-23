# Phase 11.5 — Frontend Foundation: Design System + Performance Architecture

**Track:** Frontend · **Depends on:** 11.0 (FPS overlay/budgets) · **Status:** Planned

> Read the roadmap index first. This is the **easy-wins, perf-positive** base of the FE revamp.
> Everything heavier (11.6–11.9) builds on the primitives established here. No WebGL yet.

---

## 1. Context

Current frontend: Tauri v2 + React 18 + TS + Tailwind, 11 pages, dark theme, glass AppShell.
Notable existing facts to respect:
- `frontend/src/index.css` defines tokens (`--accent #4c8dff`, confidence colors `--verified/strong/weak`).
- `tailwind.config.js` extends `colors` with those + Inter font.
- `AppShell.tsx` uses `backdrop-blur-[60px]` — **the exact expensive pattern** the perf guidelines
  flag (PERF-AC-002). 11.5 replaces the live blur with a cheaper proxy strategy.
- CSP in `src-tauri/tauri.conf.json`: `style-src 'self' 'unsafe-inline' + google fonts`,
  `font-src google fonts`, `script-src 'self'`. SF Pro is **not** a web font we can fetch — use the
  local macOS system font stack (`-apple-system`/`ui-sans-serif`) which exposes SF Pro on Mac; keep
  Inter as cross-platform fallback. No CSP change needed in 11.5.
- Zustand store (`useAppStore`) is minimal.

## 2. Guidelines implemented (IDs)

- **HAM-003** Display P3 color gamut · **VPT-001** variable font axis mapping (system SF Pro)
  · **VPT-002** fluid baseline alignment (4/8px grid) · **VPT-003** dynamic tabular-nums
- **PERF-RP-001** transient state for high-freq inputs · **PERF-RP-002** CSS containment
  · **PERF-AC-001** OMTA (transform/opacity only) · **PERF-AC-002** material proxy (replace live blur)
  · **PERF-AC-003** will-change promotion strategy · **PERF-IL-001** code-split by interaction
- Catalog easy wins: #5 true-dark luminance, #19 fluid 4px snapping, #82 sub-pixel shimmer (token only)

## 3. Goals

- A documented **design-token layer**: P3 colors (with sRGB fallback via `@supports`), a typographic
  scale on a 4/8px baseline grid, motion tokens (durations/easings), elevation/material tokens.
- **`framer-motion`** installed + a thin `motion/` primitives module (preconfigured springs/variants)
  so later segments don't re-derive easing curves.
- **Performance architecture utilities** every component will use:
  - transient input store (refs / Zustand transient `subscribe`) for mouse/scroll/drag — never `useState`.
  - a `<Contained>` helper / Tailwind utility applying `contain: layout paint`.
  - a `useWillChange` hook (promote on intent, remove on settle).
  - an OMTA lint rule-of-thumb doc + a `cn`-friendly set of safe animation utilities.
- **Material proxy**: replace `AppShell` live `backdrop-blur` with a pre-blurred static layer
  (image or cheap gradient) whose opacity animates instead of the blur — measurable FPS win.
- **Code-split-on-intent** wiring: heavy routes/modals dynamically import `onPointerEnter`.

## 4. Non-goals (YAGNI)

- No WebGL/Three (11.7). No haptics/native (11.8). No scroll-driven morphs (11.6).
- No new component library / no Radix expansion beyond what's installed.
- No full visual redesign of every page — establish the system + apply to AppShell + one page
  (Dashboard) as the reference implementation. Remaining pages adopt tokens incrementally.
- No custom font hosting.

## 5. Design

### Tokens
- `frontend/src/styles/tokens.css`: define P3 colors with fallback:
  ```css
  :root { --accent: #4c8dff; }
  @supports (color: color(display-p3 1 1 1)) {
    :root { --accent: color(display-p3 0.30 0.55 1.0); }
  }
  ```
  Extend Tailwind theme to read CSS vars (so P3 flows through utilities). Add `tabular`/`proportional`
  numeric utilities and a baseline-grid spacing scale (multiples of 4px).
- Typography: system SF Pro stack; fluid `font-variation-settings` via `clamp()`-driven custom props
  on key headings (VPT-001). Baseline grid documented; line-heights snap to 4px multiples (VPT-002).

### Motion primitives
- `frontend/src/motion/index.ts`: exported springs (`gentle`, `snappy`), shared variants
  (`fadeUp`, `scaleIn`), and a `prefersReducedMotion` guard that flattens all of them. **Everything
  later imports from here** so reduced-motion is honored globally.

### Perf utilities
- `frontend/src/stores/useTransientInput.ts`: Zustand store with `subscribe`-based transient updates
  + a `pointerRef` pattern; exposes `setPointer(x,y)` that does NOT trigger re-render (PERF-RP-001).
- `frontend/src/hooks/useWillChange.ts`: returns handlers that set `will-change` on enter and clear
  on animation end (PERF-AC-003).
- Tailwind plugin / utility classes: `.contain-paint` → `contain: layout paint` (PERF-RP-002).
- `frontend/src/components/ui/lazyOnIntent.tsx`: helper to prefetch a `React.lazy` chunk on
  `onPointerEnter` (PERF-IL-001).

### Material proxy
- `AppShell.tsx`: replace `backdrop-blur-[60px]` with a static pre-blurred background layer (a
  low-res blurred gradient `div` or asset) + translucency; animate opacity not blur (PERF-AC-002).
  Verify FPS during sidebar nav before/after with 11.0 overlay.

### Reference application
- Apply tokens + motion primitives to `Dashboard.tsx` as the canonical example others follow.

## 6. File-level plan

```
NEW  frontend/src/styles/tokens.css            (P3 + fallback, baseline grid, numeric utils)
NEW  frontend/src/motion/index.ts              (springs, variants, reduced-motion guard)
NEW  frontend/src/stores/useTransientInput.ts
NEW  frontend/src/hooks/useWillChange.ts
NEW  frontend/src/components/ui/lazyOnIntent.tsx
EDIT frontend/src/index.css                    (import tokens.css; remove hardcoded dupes)
EDIT frontend/tailwind.config.js               (read CSS vars; baseline spacing; numeric variants)
EDIT frontend/src/layouts/AppShell.tsx         (material proxy instead of live blur)
EDIT frontend/src/pages/Dashboard.tsx          (reference adoption of tokens + motion)
EDIT frontend/package.json                      (add framer-motion)
EDIT docs/09_DESIGN_GUIDELINES.css / new docs/FRONTEND_DESIGN_SYSTEM.md (document the system)
```

## 7. Test plan

- Frontend has Playwright (`frontend/e2e/`) but no unit runner wired. Plan:
  - `frontend/src/motion/index.test.ts` (add Vitest if absent — `# ponytail: add vitest only if no runner`):
    assert `prefersReducedMotion` flattens variants; transient store does not re-render (spy on render).
  - Playwright e2e: Dashboard renders, no console errors, AppShell nav works.
- **Manual perf gate (required):** capture idle FPS + sidebar-nav FPS before/after via 11.0 overlay;
  attach to PR. Material-proxy change must show equal-or-better FPS.

## 8. Plugin orchestration checklist

- [ ] `context7` — framer-motion v11 API, Tailwind v3 CSS-var theming, CSS `color(display-p3)` + `@supports`.
- [ ] `frontend-design` skill — aesthetic direction so this doesn't read as templated default.
- [ ] `superpowers:test-driven-development` (where a runner exists).
- [ ] `superpowers:verification-before-completion` — screenshots + FPS numbers.

## 9. Perf budget impact

Net **positive**: replacing live `backdrop-filter` with a proxy should improve scroll/nav FPS.
`framer-motion` adds ~30–50KB gz — within the 11.5 bundle budget; tree-shaken, animations are OMTA.
Verify bundle delta in `vite build` report.

## 10. Risks & mitigations

- *P3 colors look off on sRGB displays* → always provide sRGB fallback via `@supports`; test both.
- *framer-motion bundle creep* → import specific APIs; lazy-load motion-heavy components in later segments.
- *SF Pro unavailable off-Mac* → Inter fallback in stack; this app targets macOS (ADR-005) so acceptable.

## 11. Definition of Done

Token layer (P3+fallback, baseline grid, numerics), motion primitives with global reduced-motion,
perf utilities (transient input, will-change, containment, lazy-on-intent), AppShell material proxy,
Dashboard reference adoption, design-system doc — committed, FPS before/after attached, e2e green.
