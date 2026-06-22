import { useMemo } from "react";

/**
 * Scoped `will-change` promotion (PERF-AC-003).
 *
 * `will-change` hints the browser to give an element its own compositor layer,
 * which makes transform/opacity animations smooth — but a layer left up
 * permanently wastes GPU memory and can *hurt* performance. So promote on
 * intent (pointer enter / animation start) and release on settle (leave / end).
 *
 * Spread the returned handlers onto the animated element:
 *   <div {...useWillChange()} className="transition-transform" />
 */
export function useWillChange(property = "transform") {
  return useMemo(() => {
    const promote = (e: { currentTarget: HTMLElement }) => {
      e.currentTarget.style.willChange = property;
    };
    const settle = (e: { currentTarget: HTMLElement }) => {
      e.currentTarget.style.willChange = "auto";
    };
    return {
      onPointerEnter: promote,
      onPointerLeave: settle,
      onTransitionEnd: settle,
      onAnimationEnd: settle,
    };
  }, [property]);
}
