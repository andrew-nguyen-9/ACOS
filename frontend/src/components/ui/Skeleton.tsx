import { m } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Skeleton primitives (Phase 11.6, ASP-002).
 *
 * Structural twins of real content that mask latency without a spinner. They
 * mirror the target view's dimensions so swapping skeleton → content causes no
 * layout shift (CLS=0). Only mounted after the 200ms gate (`useDeferredLoading`).
 */

/** A single pulsing block. `animate-pulse` is opacity-only (OMTA / compositor). */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-white/[0.06]", className)} />;
}

/**
 * Generic page skeleton used as the router fallback. Mirrors the shared page
 * frame (p-8, header row + stat cards + a list) so any lazy route fades in over
 * a same-shaped placeholder instead of a centered spinner.
 */
export function PageSkeleton() {
  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.18 }}
      className="flex h-full flex-col gap-6 p-8"
      aria-hidden
    >
      {/* Header */}
      <div className="flex items-center gap-4">
        <Skeleton className="size-12 rounded-2xl" />
        <div className="flex flex-col gap-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-64" />
        </div>
      </div>
      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-[22px]" />
        ))}
      </div>
      {/* List rows */}
      <div className="flex flex-1 flex-col gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-2xl" />
        ))}
      </div>
    </m.div>
  );
}
