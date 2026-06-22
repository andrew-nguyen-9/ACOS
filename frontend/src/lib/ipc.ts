/**
 * IPC batching (Phase 11.8, PERF-IPC-001).
 *
 * High-frequency Tauri invokes (window resize, drag) must never hit the bridge
 * per-event. `batchedInvoke` collapses every call made within one frame to a
 * single invoke per command — the last payload wins — flushed on the next rAF.
 */
import { invoke as tauriInvoke } from "@tauri-apps/api/core";

type InvokeFn = (cmd: string, args?: unknown) => unknown;
type Scheduler = (cb: () => void) => void;

/** True inside the packaged Tauri webview; false in vite dev / jsdom / e2e. */
export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Build a frame-coalescing invoker. Pure of any Tauri/DOM coupling (both the
 * invoke fn and the scheduler are injected), so the coalescing is unit-testable.
 */
export function createBatchedInvoke(
  invoke: InvokeFn,
  schedule: Scheduler = (cb) => requestAnimationFrame(cb),
): (cmd: string, args?: unknown) => void {
  const pending = new Map<string, unknown>();
  let scheduled = false;

  const flush = () => {
    scheduled = false;
    for (const [cmd, args] of pending) invoke(cmd, args);
    pending.clear();
  };

  return (cmd, args) => {
    pending.set(cmd, args);
    if (!scheduled) {
      scheduled = true;
      schedule(flush);
    }
  };
}

// App-wide batcher. Outside Tauri it no-ops (still coalesces, but the invoke is a
// guarded swallow) so callers can fire freely in vite dev / tests.
export const batchedInvoke = createBatchedInvoke((cmd, args) => {
  if (!isTauri()) return;
  void (tauriInvoke as InvokeFn)(cmd, args);
});
