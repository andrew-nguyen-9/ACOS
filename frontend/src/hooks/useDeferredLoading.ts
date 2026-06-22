import { useEffect, useState } from "react";

/**
 * Perceptual load masking (Phase 11.6, ASP-002 — the 200ms rule).
 *
 * Returns `false` while loading until `delay` ms have passed, then `true`.
 * Sub-200ms loads resolve before the timer fires, so the skeleton never flashes
 * (a flash reads as slower than no loader at all). Reset whenever `loading` flips.
 */
export function useDeferredLoading(loading: boolean, delay = 200): boolean {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!loading) {
      setShow(false);
      return;
    }
    const id = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(id);
  }, [loading, delay]);

  return show;
}
