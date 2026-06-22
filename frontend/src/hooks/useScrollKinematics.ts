import { type RefObject } from "react";
import { useScroll, useTransform, type MotionValue } from "framer-motion";
import { prefersReducedMotion } from "@/motion";

/**
 * Scroll-driven kinematics (Phase 11.6, KMP-002).
 *
 * Thin wrapper over `useScroll` + `useTransform` that binds a scroll container's
 * position to transform/opacity MotionValues — driven on the compositor, off the
 * main thread, never touching layout-thrashing props. Consumers spread
 * `headerStyle` onto a collapsing header and bind `progressScaleX` to a progress
 * bar (`style={{ scaleX, transformOrigin: "left" }}`).
 *
 * Reduced motion: the positional collapse (`y`) is dropped to a constant so the
 * header doesn't slide; opacity easing is retained as a gentle cross-fade.
 */
export interface ScrollKinematics {
  scrollYProgress: MotionValue<number>;
  headerStyle: { opacity: MotionValue<number>; y: MotionValue<number> };
  progressScaleX: MotionValue<number>;
}

export function useScrollKinematics(
  container: RefObject<HTMLElement>,
  collapseRange = 120,
): ScrollKinematics {
  const { scrollY, scrollYProgress } = useScroll({ container });
  const reduce = prefersReducedMotion();

  const opacity = useTransform(scrollY, [0, collapseRange], [1, 0.55]);
  const y = useTransform(scrollY, [0, collapseRange], [0, reduce ? 0 : -8]);

  return {
    scrollYProgress,
    headerStyle: { opacity, y },
    progressScaleX: scrollYProgress,
  };
}
