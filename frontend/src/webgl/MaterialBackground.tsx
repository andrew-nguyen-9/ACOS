import { Suspense, lazy, useEffect, useState } from "react";
import { resolveEffectTier, type EffectTier } from "@/lib/capability";
import { setPointer } from "@/stores/useTransientInput";

/**
 * Entry-chunk shim for the WebGL material (Phase 11.7).
 *
 * Stays tiny and `three`-free so the entry bundle is unaffected: it only resolves
 * the effective tier and `React.lazy`-loads the heavy canvas when the tier is on.
 * When the tier is `off` (no WebGL, reduced-motion, or user choice) it renders
 * nothing and the static 11.5 aurora behind it is the material.
 */
const MaterialCanvas = lazy(() => import("./MaterialCanvas"));

/** Feed the transient pointer store from a single passive window listener. */
function usePointerTracking(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    // Seed to viewport center so the focus glow starts centered instead of
    // snapping from the top-left corner before the first pointer move.
    setPointer(window.innerWidth / 2, window.innerHeight / 2);
    const onMove = (e: PointerEvent) => setPointer(e.clientX, e.clientY);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [active]);
}

export default function MaterialBackground() {
  const [tier, setTier] = useState<EffectTier>(resolveEffectTier);

  // Re-resolve when the user changes the Settings toggle or the OS reduced-motion
  // preference flips — keeps the material live without a reload.
  useEffect(() => {
    const reeval = () => setTier(resolveEffectTier());
    window.addEventListener("acos:effects-changed", reeval);
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", reeval);
    return () => {
      window.removeEventListener("acos:effects-changed", reeval);
      mq.removeEventListener("change", reeval);
    };
  }, []);

  usePointerTracking(tier !== "off");

  if (tier === "off") return null;
  return (
    <Suspense fallback={null}>
      <MaterialCanvas reduced={tier === "reduced"} />
    </Suspense>
  );
}
