/**
 * Singleton animation clock with App-Nap throttling (Phase 11.7, DMI-003).
 *
 * The single pause/resume authority for every animation loop in the app (the
 * WebGL material, 11.6 scroll loops, future 11.9 particles). It drives a shared
 * rAF and hands subscribers a continuous elapsed-seconds value. When the window
 * is hidden (`visibilitychange`) or the Tauri window loses focus, it parks the
 * rAF so the GPU/CPU cost of background animation drops to ~0 — mandatory in this
 * segment for battery, not optional.
 *
 * `elapsed` is accumulated only while running, so pausing never produces a time
 * jump in the shader when the window comes back.
 */
type FrameCallback = (elapsedSeconds: number) => void;

const subscribers = new Set<FrameCallback>();
let rafId: number | null = null;
let paused = false;
let elapsed = 0;
let lastNow = 0;

const now = (): number =>
  typeof performance !== "undefined" ? performance.now() : Date.now();

function tick(t: number): void {
  elapsed += (t - lastNow) / 1000;
  lastNow = t;
  for (const cb of subscribers) cb(elapsed);
  rafId = requestAnimationFrame(tick);
}

function ensureRunning(): void {
  if (rafId !== null || paused || subscribers.size === 0) return;
  lastNow = now();
  rafId = requestAnimationFrame(tick);
}

function stop(): void {
  if (rafId === null) return;
  cancelAnimationFrame(rafId);
  rafId = null;
}

/** Add a per-frame callback; starts the clock. Returns an unsubscribe fn. */
export function subscribe(cb: FrameCallback): () => void {
  subscribers.add(cb);
  ensureRunning();
  return () => {
    subscribers.delete(cb);
    if (subscribers.size === 0) stop();
  };
}

/** Park the clock (window hidden/blurred). Idempotent. */
export function pause(): void {
  paused = true;
  stop();
}

/** Un-park and resume if anything is subscribed. Idempotent. */
export function resume(): void {
  paused = false;
  ensureRunning();
}

/** True while the rAF loop is scheduled (for tests / introspection). */
export function isRunning(): boolean {
  return rafId !== null;
}

// ── App-Nap wiring (runs once on import) ────────────────────────────────────
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    document.hidden ? pause() : resume();
  });
}

// Tauri window focus (DMI-003). Dynamic + guarded: outside Tauri (vite dev,
// jsdom tests) the import resolves but the listener simply never fires.
if (typeof window !== "undefined" && import.meta.env.PROD) {
  void import("@tauri-apps/api/window")
    .then(({ getCurrentWindow }) =>
      getCurrentWindow().onFocusChanged(({ payload: focused }) => {
        focused ? resume() : pause();
      }),
    )
    .catch(() => {});
}
