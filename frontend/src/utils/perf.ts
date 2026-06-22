/**
 * Dev-only performance instrumentation (Phase 11.0).
 *
 * Pure, framework-free helpers so they can be unit-reasoned and tree-shaken out
 * of production. Nothing here should run in a prod build — call sites are gated
 * on `import.meta.env.DEV`.
 */

/**
 * Rolling FPS from a fixed-size window of frame timestamps.
 *
 * FPS = (frames - 1) / elapsed-seconds across the window. Kept as plain logic
 * (no React state) so the overlay can drive it from a ref at 60–120Hz without
 * re-rendering every frame (see plan: PERF-RP-001).
 */
export class FpsMeter {
  private readonly times: number[] = [];
  constructor(private readonly windowSize = 60) {}

  /** Record a frame timestamp (ms, e.g. `performance.now()`); returns rolling FPS. */
  tick(now: number): number {
    this.times.push(now);
    // ponytail: O(n) shift on a 60-element array is free; swap for a true ring
    // buffer only if windowSize ever grows into the thousands.
    if (this.times.length > this.windowSize) this.times.shift();
    if (this.times.length < 2) return 0;
    const span = this.times[this.times.length - 1] - this.times[0];
    return span > 0 ? ((this.times.length - 1) * 1000) / span : 0;
  }
}

/** Drop a User Timing mark for an interaction so it shows in DevTools traces. */
export function markInteraction(name: string): void {
  performance.mark(`acos:${name}`);
}

/**
 * Log long tasks (>50ms — the jank threshold) to the console while active.
 * Returns a disposer; `longtask` is unsupported in some browsers, so guard.
 */
export function measureLongTasks(): () => void {
  if (typeof PerformanceObserver === "undefined") return () => {};
  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        // eslint-disable-next-line no-console
        console.warn(`[perf] long task ${entry.duration.toFixed(1)}ms`, entry);
      }
    });
    observer.observe({ entryTypes: ["longtask"] });
    return () => observer.disconnect();
  } catch {
    return () => {};
  }
}

// Runnable self-check (no JS test runner is wired in this repo). Fires only in
// dev; cheap, and fails loudly if the rolling-FPS math regresses.
if (import.meta.env.DEV) {
  const m = new FpsMeter(10);
  m.tick(0);
  const fps = m.tick(1000); // 2 frames, 1s apart → 1 fps
  console.assert(Math.abs(fps - 1) < 1e-9, `FpsMeter math broken: got ${fps}`);
}
