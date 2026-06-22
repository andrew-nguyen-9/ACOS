import { useEffect, useRef, useState } from "react";
import { m } from "framer-motion";
import { Sparkles } from "lucide-react";
import { onCelebrate } from "@/lib/celebrate";
import { resolveEffectTier } from "@/lib/capability";

/**
 * Off-tier celebration flourish (Phase 11.9, HVP-001 degradation).
 *
 * When the WebGL particle layer can't run (effects Off, no WebGL, or OS
 * reduced-motion — all resolve to the `off` tier), a celebration still needs a
 * tasteful, accessible payoff. This is an opacity-only glow + status message,
 * safe under reduced motion (the app's MotionConfig strips transforms). On the
 * Full/Reduced tiers it stays out of the way — the particles own the moment.
 */
export default function CelebrationFallback() {
  const [shown, setShown] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const off = onCelebrate(() => {
      if (resolveEffectTier() !== "off") return; // particles handle on/reduced
      setShown(true);
      // Reset the dismiss timer so back-to-back celebrations extend, not truncate.
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setShown(false), 1800);
    });
    return () => {
      off();
      clearTimeout(timer.current);
    };
  }, []);

  if (!shown) return null;
  return (
    <m.div
      role="status"
      aria-live="polite"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center"
    >
      <div className="flex items-center gap-3 rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-6 py-4 shadow-panel">
        <Sparkles className="size-5 text-[var(--accent)]" />
        <span className="text-sm font-semibold text-neutral-50">Nicely done.</span>
      </div>
    </m.div>
  );
}
