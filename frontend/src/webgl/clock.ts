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
// App-Nap pause sources are independent (document visibility, Tauri window
// focus, manual). The clock runs only when *no* source is parking it — a resume
// from one source must not clear a pause still held by another.
const pauseReasons = new Set<string>();
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
  if (rafId !== null || pauseReasons.size > 0 || subscribers.size === 0) return;
  lastNow = now();
  rafId = requestAnimationFrame(tick);
}

function stop(): void {
  if (rafId === null) return;
  cancelAnimationFrame(rafId);
  rafId = null;
}

/** Park the clock for a named source. Idempotent per source. */
function park(reason: string): void {
  pauseReasons.add(reason);
  stop();
}

/** Clear a named source; resumes only when no source is parking it. */
function unpark(reason: string): void {
  pauseReasons.delete(reason);
  ensureRunning();
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

/** Park the clock from the manual/imperative source. Idempotent. */
export function pause(): void {
  park("manual");
}

/** Clear the manual pause; resumes only if no other source is still parking. */
export function resume(): void {
  unpark("manual");
}

/** True while the rAF loop is scheduled (for tests / introspection). */
export function isRunning(): boolean {
  return rafId !== null;
}

// ── App-Nap wiring (runs once on import) ────────────────────────────────────
// Each source parks/unparks its own reason; the clock runs only when both agree
// it should (e.g. a hidden tab stays parked even if the window regains focus).
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    document.hidden ? park("visibility") : unpark("visibility");
  });
}

// Tauri window focus (DMI-003). Dynamic + guarded: outside Tauri (vite dev,
// jsdom tests) the import resolves but the listener simply never fires.
if (typeof window !== "undefined" && import.meta.env.PROD) {
  void import("@tauri-apps/api/window")
    .then(({ getCurrentWindow }) =>
      getCurrentWindow().onFocusChanged(({ payload: focused }) => {
        focused ? unpark("focus") : park("focus");
      }),
    )
    .catch(() => {});
}
