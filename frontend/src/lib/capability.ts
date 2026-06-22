/**
 * Visual-effects capability tier (Phase 11.7).
 *
 * The WebGL material is a progressive enhancement, never a requirement. The
 * effective tier is the user's preference clamped by what the device can
 * honestly deliver: no WebGL or OS reduced-motion drops to `off`, where the app
 * falls back to the cheap static aurora from 11.5.
 */
import { prefersReducedMotion } from "@/motion";

export type EffectTier = "full" | "reduced" | "off";

const STORAGE_KEY = "acos:visual-effects";

/** Is a WebGL context obtainable? Cached — context creation isn't free. */
let webglCache: boolean | undefined;
export function supportsWebGL(): boolean {
  if (webglCache !== undefined) return webglCache;
  try {
    const canvas = document.createElement("canvas");
    webglCache = !!(
      canvas.getContext("webgl") || canvas.getContext("experimental-webgl")
    );
  } catch {
    webglCache = false;
  }
  return webglCache;
}

/** Pure tier resolution — the unit boundary (testable without a GPU). */
export function pickTier(opts: {
  pref: EffectTier;
  webgl: boolean;
  reducedMotion: boolean;
}): EffectTier {
  if (!opts.webgl || opts.reducedMotion) return "off";
  return opts.pref;
}

/** Saved preference (localStorage); defaults to Full on first run. */
export function getEffectPreference(): EffectTier {
  const raw =
    typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
  return raw === "full" || raw === "reduced" || raw === "off" ? raw : "full";
}

export function setEffectPreference(pref: EffectTier): void {
  if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, pref);
}

/** Effective tier: saved preference clamped by live device capability. */
export function resolveEffectTier(): EffectTier {
  return pickTier({
    pref: getEffectPreference(),
    webgl: supportsWebGL(),
    reducedMotion: prefersReducedMotion(),
  });
}
