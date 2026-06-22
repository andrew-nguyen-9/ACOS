# Phase 11.6 — Frontend Kinematics + State Perception

**Track:** Frontend · **Depends on:** 11.5 (motion primitives, transient store, perf utils) · **Status:** Planned

> Read the roadmap index first. Mid-tier intensity: physics-based motion + perceived-latency work.
> Still no WebGL. Everything animates transform/opacity only (OMTA).

---

## 1. Context

11.5 gave springs, a transient input store, will-change, and lazy-on-intent. 11.6 uses them to make
the app *feel* alive and instant: momentum-aware transitions, scroll-bound motion, layout projection,
predictive prefetch, and skeleton choreography that masks latency instead of flashing spinners.

The current loading pattern is a centered spinner (`PageFallback` in `App.tsx`, `LoadingSpinner`).
That's the thing 11.6 replaces with perceptual load masking.

## 2. Guidelines implemented (IDs)

- **KMP-001** interruptible velocity transfer · **KMP-002** scroll-driven kinematics
  · **KMP-003** layout projection (LayoutGroup)
- **ASP-001** predictive intent & prefetching · **ASP-002** perceptual load masking (200ms rule)
  · **ASP-003** concurrent React `startTransition`
- **PERF-RP-003** granular VDOM virtualization (`@tanstack/react-virtual` + `content-visibility:auto`)
- Catalog: #81 elastic over-scroll, #99 momentum pill switches, #89 magnetic button (subtle), #93 zero-latency flips

## 3. Goals

- **Interruptible velocity transfer**: draggable/dismissable surfaces (modals, sheets, the Copilot
  panel) read pointer velocity on release and feed it into the exit spring (KMP-001).
- **Scroll-driven kinematics**: bind `useScroll`/`useTransform` to header collapse, parallax, and
  progress affordances — off main thread, transform/opacity only (KMP-002).
- **Layout projection**: shared-element transitions via `LayoutGroup`/`layoutId` (e.g., a list card
  expanding into a detail view; avatar moving sidebar→header) (KMP-003).
- **Predictive prefetch**: on pointer-trajectory/`onPointerEnter` toward nav items and primary
  actions, prefetch the route chunk **and** warm the backend call (ASP-001). Negative latency.
- **Perceptual load masking**: <200ms → no loader; >200ms → fade in a skeleton mirroring the real
  DOM (ASP-002). Replace `PageFallback` spinner.
- **Concurrent rendering**: wrap heavy list filters/search in `startTransition` (ASP-003).
- **Virtualization**: any list >50 items uses `@tanstack/react-virtual` + `content-visibility:auto`
  (Applications CRM, Learning, large resume bullet lists) (PERF-RP-003).

## 4. Non-goals (YAGNI)

- No WebGL/shaders (11.7). No native haptics (11.8).
- No gyroscope input. No full gesture system — only the surfaces that already drag (modals/panels).
- Predictive prefetch is best-effort (idle prefetch), not a speculative-execution framework.
- Skeletons only for the 2–3 highest-latency views, not every component.

## 5. Design

- `frontend/src/hooks/useVelocityDismiss.ts`: wraps a draggable surface; on dragEnd reads
  `info.velocity` (framer-motion) and animates exit with that initial velocity (KMP-001).
- `frontend/src/hooks/useScrollKinematics.ts`: thin wrapper over `useScroll`+`useTransform` with
  cubic-bezier maps; consumers pass ranges. Applied to a collapsing page header.
- Wrap routed content in `<LayoutGroup>`; add `layoutId` to list↔detail shared elements (KMP-003).
- `frontend/src/services/prefetch.ts`: `prefetchRoute(name)` (dynamic import) + `warm(endpoint)`
  (fire-and-forget GET, dedup). Wire to `AppShell` nav `onPointerEnter` and key CTAs (ASP-001).
- `frontend/src/components/ui/Skeleton.tsx` + `useDeferredLoading(delay=200)`: only show skeleton if
  load exceeds 200ms; skeletons are structural twins of target pages (ASP-002). Replace `PageFallback`.
- `frontend/src/components/ui/VirtualList.tsx`: `@tanstack/react-virtual` wrapper + `content-visibility`.
  Adopt in `ApplicationsPage` and `LearningPage` lists.
- Search/filter inputs: wrap state updates in `startTransition`; keep the input controlled via
  transient ref where high-frequency (ASP-003 + PERF-RP-001).

## 6. File-level plan

```
NEW  frontend/src/hooks/useVelocityDismiss.ts
NEW  frontend/src/hooks/useScrollKinematics.ts
NEW  frontend/src/hooks/useDeferredLoading.ts
NEW  frontend/src/services/prefetch.ts
NEW  frontend/src/components/ui/Skeleton.tsx
NEW  frontend/src/components/ui/VirtualList.tsx
EDIT frontend/src/App.tsx                       (LayoutGroup wrap; skeleton instead of spinner fallback)
EDIT frontend/src/layouts/AppShell.tsx          (prefetch on nav hover)
EDIT frontend/src/pages/ApplicationsPage.tsx    (VirtualList + startTransition filters)
EDIT frontend/src/pages/LearningPage.tsx        (VirtualList)
EDIT frontend/src/components/copilot/*          (velocity-dismiss on the copilot panel)
EDIT frontend/package.json                       (add @tanstack/react-virtual)
```

## 7. Test plan

- Unit (Vitest where available): `useDeferredLoading` shows nothing <200ms, skeleton after; prefetch
  dedups; velocity mapping clamps.
- Playwright e2e: open list → virtualized rows render and scroll without console errors; navigate
  list→detail shows layout transition; hovering nav prefetches (assert network warm call fired).
- **Manual perf gate (required):** scroll a 500-item list — long-tasks during scroll must be 0
  (11.0 trace); FPS ≥60. Modal fling-dismiss stays at 60fps. Attach trace to PR.

## 8. Plugin orchestration checklist

- [ ] `context7` — framer-motion `useScroll`/`LayoutGroup`/drag velocity; `@tanstack/react-virtual`; React `startTransition`.
- [ ] `frontend-design` — motion taste (avoid overshoot/AI-slop bounce).
- [ ] `chrome-devtools` skill / Playwright — capture performance traces for the perf gate.
- [ ] `superpowers:verification-before-completion`.

## 9. Perf budget impact

Virtualization **reduces** DOM node count (target <1500) — net win on large lists. Scroll kinematics
must stay transform/opacity (no layout). `@tanstack/react-virtual` ~5KB gz. Predictive prefetch uses
idle time; cap concurrency to avoid thrashing the backend. Verify long-task count == 0 during scroll.

## 10. Risks & mitigations

- *Layout projection jank on big DOM* → only apply `layoutId` to small shared elements, not whole pages.
- *Prefetch wastes backend cycles* → dedup + only warm idempotent GETs; respect App-Nap (11.7 will
  pause when hidden; here at least guard with `document.visibilityState`).
- *Skeleton mismatch causes shift* → skeletons must mirror final layout dimensions (CLS=0).

## 11. Definition of Done

Velocity-dismiss, scroll kinematics, layout projection, predictive prefetch, 200ms skeleton masking,
startTransition filters, and virtualized lists implemented; perf gate (0 long-tasks on scroll, 60fps
fling) attached; e2e green; bundle delta within budget.
