import { useMemo, useState } from "react";
import { useMotionValue, useSpring, useTransform, type MotionValue } from "framer-motion";
import { prefersReducedMotion } from "@/motion";
import { debounce } from "@/lib/debounce";

/**
 * Quantum cover-letter tone morphing (Phase 11.9, RCL-003).
 *
 * One slider (0 = Traditional, 1 = Bold) drives two things at once:
 *   1. an *instant* client-side typography morph (this hook), and
 *   2. a *debounced* backend regeneration with a `tone` param (the caller).
 *
 * Variable-font note: index.html loads Inter at STATIC weights only, so
 * `font-variation-settings` would silently no-op. We morph the axes a static
 * family CAN honor — weight (snaps through 500/600), tracking, and leading —
 * which still reads as a fluid tonal shift. No extra font request / CSP change.
 */
export interface ToneType {
  fontWeight: number;
  letterSpacing: number; // em
  lineHeight: number;
}

// Endpoints of the morph. Traditional = lighter, airier, more tracking.
const TRADITIONAL: ToneType = { fontWeight: 420, letterSpacing: 0.01, lineHeight: 1.75 };
const BOLD: ToneType = { fontWeight: 680, letterSpacing: -0.015, lineHeight: 1.4 };

const clamp01 = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Pure slider→typography mapping. Unit-tested; reused for the live morph. */
export function toneToType(tone: number): ToneType {
  const t = clamp01(tone);
  return {
    fontWeight: Math.round(lerp(TRADITIONAL.fontWeight, BOLD.fontWeight, t)),
    letterSpacing: lerp(TRADITIONAL.letterSpacing, BOLD.letterSpacing, t),
    lineHeight: lerp(TRADITIONAL.lineHeight, BOLD.lineHeight, t),
  };
}

export interface ToneMorphStyle {
  fontWeight: MotionValue<number>;
  letterSpacing: MotionValue<string>;
  lineHeight: MotionValue<number>;
}

export interface UseToneMorph {
  tone: number;
  setTone: (value: number) => void;
  style: ToneMorphStyle;
}

/**
 * @param onCommit  debounced backend regeneration with the new tone (best-effort)
 * @param initial   starting tone (0..1), default balanced
 */
export function useToneMorph(
  onCommit?: (tone: number) => void,
  initial = 0.5,
): UseToneMorph {
  const [tone, setToneState] = useState(initial);
  const reduce = useMemo(() => prefersReducedMotion(), []);

  const raw = useMotionValue(initial);
  // Springed source for a fluid morph; reduced-motion reads the raw value (instant).
  const spring = useSpring(raw, { stiffness: 170, damping: 26 });
  const src = reduce ? raw : spring;

  const style: ToneMorphStyle = {
    fontWeight: useTransform(src, (t) => toneToType(t).fontWeight),
    letterSpacing: useTransform(src, (t) => `${toneToType(t).letterSpacing}em`),
    lineHeight: useTransform(src, (t) => toneToType(t).lineHeight),
  };

  const commit = useMemo(
    () => (onCommit ? debounce(onCommit, 450) : undefined),
    [onCommit],
  );

  const setTone = (value: number) => {
    const t = clamp01(value);
    setToneState(t);
    raw.set(t);
    commit?.(t);
  };

  return { tone, setTone, style };
}
