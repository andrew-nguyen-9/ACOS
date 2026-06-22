import { useEffect, useRef, type RefObject } from "react";
import { subscribePointer } from "@/stores/useTransientInput";

/**
 * Cursor-mapped specular highlight (Phase 11.7, HAM-002).
 *
 * Maps the transient pointer to `--spec-x/--spec-y` CSS custom properties on the
 * element, so a CSS `radial-gradient` highlight tracks the cursor. CSS does the
 * per-card highlight; the shader does only the background — no per-card WebGL
 * context (multiple GL contexts kill perf).
 *
 * Updates fire on pointer *movement* (transient store), not every frame, so a
 * still cursor costs nothing. The element rect is cached and refreshed on
 * scroll/resize, so the per-move work is pure math + two style writes (no layout
 * read in the hot path).
 *
 * ponytail: one store subscription per card. Fine for the handful of primary
 * cards/buttons that opt in; switch to a single delegated listener if hundreds.
 */
export function useSpecular<T extends HTMLElement>(): RefObject<T> {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let rect = el.getBoundingClientRect();
    const refreshRect = () => {
      rect = el.getBoundingClientRect();
    };
    window.addEventListener("scroll", refreshRect, { passive: true, capture: true });
    window.addEventListener("resize", refreshRect);

    const unsub = subscribePointer((p) => {
      const x = ((p.x - rect.left) / rect.width) * 100;
      const y = ((p.y - rect.top) / rect.height) * 100;
      el.style.setProperty("--spec-x", `${x}%`);
      el.style.setProperty("--spec-y", `${y}%`);
    });

    return () => {
      unsub();
      window.removeEventListener("scroll", refreshRect, { capture: true });
      window.removeEventListener("resize", refreshRect);
    };
  }, []);

  return ref;
}
