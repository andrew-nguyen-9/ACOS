/**
 * Phase 13.2 — optional, non-blocking resume strategy hints.
 *
 * Surfaces POST /flywheel/strategy as additive advice tied to resume sections.
 * Every hint is the SERVER's recommendation rendered as-is — no client
 * re-ranking or re-thresholding — and carries its ADR-006 confidence. Sparse
 * data arrives already degraded to weak_inference + generic guidance; we render
 * that verbatim and never invent a "best practice" (CLAUDE.md #1, TRAP 2).
 * Unknown industry (`flagged`) shows a flag, never a guessed industry label
 * (TRAP 3). `rec == null` renders nothing, so the editor is byte-identical when
 * hints are absent or the optional fetch failed (TRAP 1).
 */
import { useState } from "react";
import { Lightbulb, AlertTriangle, X } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import type { StrategyRecommendation } from "@/types/flywheel";

function Chips({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-[11px] font-medium text-[#a1a1a1] mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((it) => (
          <span
            key={it}
            className="text-xs px-2 py-0.5 rounded-full bg-white/[0.06] text-neutral-300 border border-white/10"
          >
            {it}
          </span>
        ))}
      </div>
    </div>
  );
}

export function StrategyHints({ rec }: { rec: StrategyRecommendation | null }) {
  const [dismissed, setDismissed] = useState(false);
  if (!rec || dismissed) return null;

  return (
    <GlassCard className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb className="size-4 text-[#FF9F0A]" />
          <span className="text-sm font-medium text-neutral-200">Strategy hints</span>
        </div>
        <div className="flex items-center gap-2">
          <ConfidenceBadge level={rec.confidence} />
          <button
            onClick={() => setDismissed(true)}
            aria-label="Dismiss strategy hints"
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {rec.flagged ? (
        <div className="flex items-center gap-1.5 self-start px-2 py-1 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20 text-xs">
          <AlertTriangle className="size-3.5" />
          Unverified industry — generic guidance only
        </div>
      ) : (
        <p className="text-xs text-[#a1a1a1]">Tuned for: {rec.industry}</p>
      )}

      <Chips label="Suggested section order" items={rec.section_order} />
      <Chips label="Recommended skills" items={rec.recommended_skills} />
      <Chips label="Keyword targets" items={rec.keyword_targets} />

      {rec.notes && <p className="text-xs text-[#a1a1a1] leading-relaxed">{rec.notes}</p>}
      {rec.evidence.length > 0 && (
        <p className="text-[11px] text-neutral-600">
          Based on {rec.evidence.length} of your outcome signal{rec.evidence.length === 1 ? "" : "s"}.
        </p>
      )}
    </GlassCard>
  );
}
