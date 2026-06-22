import { ROUTES } from "@/routes";

/**
 * Predictive prefetch (Phase 11.6, ASP-001) — "negative latency".
 *
 * On intent (nav hover, primary CTA hover) we (a) warm the route's JS chunk and
 * (b) fire the backend GET it will need, so the data is in flight before the
 * click lands. Best-effort only: deduped, idempotent GETs, skipped when the tab
 * is hidden, and capped so we never thrash the backend.
 */

const API_BASE = "http://localhost:8000/api/v1";

// One warm per endpoint per session is enough — the page's own fetch dedupes
// against the browser cache. `warmed` guards repeat hovers; `inFlight` caps
// concurrency so a burst of hovers can't open dozens of sockets.
let warmed = new Set<string>();
let inFlight = 0;
const MAX_CONCURRENT = 4;

/** Warm a route's code chunk (reuses the router's `lazyOnIntent` prefetch). */
export function prefetchRoute(path: string): void {
  ROUTES.find((r) => r.path === path)?.prefetch();
}

// The backend GET(s) a route fetches on mount. Only data-heavy routes are worth
// warming; the rest just prefetch their chunk. ponytail: extend as pages grow.
const ROUTE_WARMERS: Record<string, string[]> = {
  "/applications": ["/applications/"],
  "/learning": ["/learning/report", "/applications/"],
};

/** Prefetch a route's chunk AND warm its backend data, on hover/focus intent. */
export function warmRoute(path: string): void {
  prefetchRoute(path);
  ROUTE_WARMERS[path]?.forEach(warm);
}

/**
 * Fire a fire-and-forget idempotent GET to pre-populate the browser cache.
 * `path` is relative to the API base (e.g. "/applications/").
 */
export function warm(path: string): void {
  if (warmed.has(path)) return;
  if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
  if (inFlight >= MAX_CONCURRENT) return;

  warmed.add(path);
  inFlight++;
  // ponytail: GET only, errors ignored — this is a cache primer, not a load path.
  void fetch(`${API_BASE}${path}`, { method: "GET" })
    .catch(() => {})
    .finally(() => {
      inFlight--;
    });
}

/** Test-only reset of the dedup/concurrency state. */
export function __resetPrefetch(): void {
  warmed = new Set<string>();
  inFlight = 0;
}
