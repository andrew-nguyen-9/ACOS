import { useRef } from "react";
import type { PanInfo, Transition } from "framer-motion";
import { springs } from "@/motion";

/**
 * Interruptible velocity transfer (Phase 11.6, KMP-001).
 *
 * A draggable surface (modal / sheet / panel) reads the pointer velocity at the
 * moment of release and feeds it straight into the exit spring, so a fast fling
 * keeps flying and a slow drag-back settles. This is what makes a dismiss feel
 * like the surface has momentum instead of snapping to a canned animation.
 *
 * The pure pieces (`shouldDismiss`, `dismissTransition`) are unit-tested; the
 * hook just wires framer's drag callbacks to them.
 */

/** Cap release velocity so a flick on a trackpad can't launch a 50000px/s spring. */
export const MAX_DISMISS_VELOCITY = 2500;

const clamp = (v: number, max: number) => Math.max(-max, Math.min(max, v));

export interface DismissThresholds {
  /** px dragged past which we dismiss regardless of speed. */
  offset: number;
  /** px/s release speed past which we dismiss regardless of distance. */
  velocity: number;
}

/** Dismiss if dragged far enough OR flung fast enough (either is sufficient). */
export function shouldDismiss(
  offset: number,
  velocity: number,
  t: DismissThresholds,
): boolean {
  return offset >= t.offset || velocity >= t.velocity;
}

/** Exit spring seeded with the release velocity (clamped). */
export function dismissTransition(velocity: number) {
  return {
    type: "spring" as const,
    stiffness: 260,
    damping: 30,
    velocity: clamp(velocity, MAX_DISMISS_VELOCITY),
  };
}

export interface UseVelocityDismiss {
  /** Spread onto the draggable `m.*` element. */
  dragProps: {
    drag: "y";
    dragElastic: number;
    dragConstraints: { top: number; bottom: number };
    onDragEnd: (e: PointerEvent | MouseEvent | TouchEvent, info: PanInfo) => void;
  };
  /** Transition to hand the exit animation; reads the captured release velocity. */
  exitTransition: () => Transition;
}

/**
 * Wire a vertical drag-to-dismiss. Call `onDismiss` to unmount the surface
 * (e.g. inside `<AnimatePresence>`); pass `exitTransition()` to the exit anim.
 */
export function useVelocityDismiss(
  onDismiss: () => void,
  thresholds: DismissThresholds = { offset: 140, velocity: 600 },
): UseVelocityDismiss {
  const velocityRef = useRef(0);

  return {
    dragProps: {
      drag: "y",
      dragElastic: 0.16,
      // Allow drag-down only; spring snaps back up if not dismissed.
      dragConstraints: { top: 0, bottom: 0 },
      onDragEnd: (_e, info) => {
        if (shouldDismiss(info.offset.y, info.velocity.y, thresholds)) {
          velocityRef.current = info.velocity.y;
          onDismiss();
        }
      },
    },
    exitTransition: () =>
      velocityRef.current > 0 ? dismissTransition(velocityRef.current) : springs.gentle,
  };
}
