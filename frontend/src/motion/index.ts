import type { Transition, Variants } from "framer-motion";

/**
 * Motion primitives (Phase 11.5).
 *
 * The single source of truth for animation in ACOS. Every component imports
 * springs/variants from here so later FE segments (11.6+) don't re-derive easing
 * curves, and so reduced-motion is honored uniformly.
 *
 * Runtime reduced-motion: the app wraps everything in
 * `<MotionConfig reducedMotion="user">` (see AppShell), which makes framer-motion
 * drop transform/layout animations and keep opacity. `flattenVariants` below is
 * the same idea for any variant we apply by hand, and is unit-tested.
 *
 * All variants animate transform/opacity only (PERF-AC-001 / OMTA) — never
 * width/height/top/left, which thrash layout.
 */

/** Preconfigured spring transitions. Physics-based, no fixed duration. */
export const springs = {
  /** Soft settle for panels, cards, page content. */
  gentle: { type: "spring", stiffness: 170, damping: 26, mass: 1 },
  /** Quick, crisp feedback for hovers, taps, small UI. */
  snappy: { type: "spring", stiffness: 420, damping: 32, mass: 0.7 },
} satisfies Record<string, Transition>;

/** Rise + fade — default entrance for content blocks. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: springs.gentle },
};

/** Scale + fade — for cards/badges/modals that "pop" into place. */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: { opacity: 1, scale: 1, transition: springs.snappy },
};

/** Parent that staggers `fadeUp`/`scaleIn` children into view. */
export const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } },
};

// Transform/position props that imply motion; reduced-motion strips these and
// keeps only opacity so the UI still cross-fades but never slides or scales.
const MOTION_KEYS = new Set([
  "x", "y", "z",
  "scale", "scaleX", "scaleY",
  "rotate", "rotateX", "rotateY", "rotateZ",
  "skew", "skewX", "skewY",
]);

/**
 * Return a reduced-motion copy of a variant set: drop transform props, keep
 * opacity, collapse every transition to instant. Pure + unit-tested.
 */
export function flattenVariants(variants: Variants): Variants {
  const out: Variants = {};
  for (const [state, def] of Object.entries(variants)) {
    if (def == null || typeof def !== "object") {
      out[state] = def;
      continue;
    }
    const clean: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(def)) {
      if (key === "transition" || MOTION_KEYS.has(key)) continue;
      clean[key] = value;
    }
    clean.transition = { duration: 0 };
    out[state] = clean as Variants[string];
  }
  return out;
}

/** True if the OS requests reduced motion. Safe to call outside React. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}
