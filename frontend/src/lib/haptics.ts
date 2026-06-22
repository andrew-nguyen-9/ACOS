/**
 * Haptic feedback wrappers (Phase 11.8, DMI-002).
 *
 * Thin, throttled, guarded shims over the Rust `haptic` command. Haptics are
 * additive — every call is best-effort and silently no-ops outside the packaged
 * Tauri app (vite dev / e2e / non-mac). Wired to: successful generation
 * (`success`), errors / destructive intent (`warn`), and lightweight commits
 * like accepting a ghost completion (`tap`).
 */
import { invoke } from "@tauri-apps/api/core";
import { isTauri } from "./ipc";

type Pattern = "tap" | "success" | "warn";

// One global throttle: a burst of UI events must not machine-gun the bridge.
const THROTTLE_MS = 60;
let last = 0;

function fire(pattern: Pattern): void {
  if (!isTauri()) return;
  const now = performance.now();
  if (now - last < THROTTLE_MS) return;
  last = now;
  void invoke("haptic", { pattern }).catch(() => {});
}

export const tap = () => fire("tap");
export const success = () => fire("success");
export const warn = () => fire("warn");
