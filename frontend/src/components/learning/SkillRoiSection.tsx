import { useEffect, useState } from "react";
import { ChevronDown, Target } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { DormantEmptyState } from "@/components/ui/DormantEmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { cn, fmtRoi } from "@/lib/utils";
import { flywheelService } from "@/services/flywheel";
import type { SkillRoiResponse } from "@/types/flywheel";

/**
 * Phase 13.1 — surfaces GET /flywheel/skills/roi inside the Learning Engine.
 *
 * Ranked, confidence-tagged, explainable. Render order = the server's ranking
 * (never re-sorted). Emphasis = the server's `recommended` list (strong + roi>0),
 * never re-derived from roi/confidence locally — so a thin-data row can't be
 * promoted client-side past the backend's n/confidence gate (ADR-006).
 */

// ponytail: self-contained fetch — request-per-view is fine (see flywheel.ts),
// no shared store until a measured re-fetch problem appears.
export function SkillRoiSection() {
  const [data, setData] = useState<SkillRoiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    flywheelService
      .getSkillRoi()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const toggle = (skill: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(skill)) next.delete(skill);
      else next.add(skill);
      return next;
    });

  const recommended = new Set(data?.recommended ?? []);
  const skills = data?.skills ?? [];

  return (
    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Target className="size-4 text-[#7e5fff]" />
        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
          Skill ROI
        </h2>
        {data?.metric && (
          <span className="ml-auto font-medium rounded-full bg-white/6 text-[#a1a1a1] text-[10px] border border-white/10 px-2 py-0.5">
            {data.metric}
          </span>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner label="Loading skill ROI…" />
        </div>
      ) : skills.length === 0 ? (
        <DormantEmptyState description="Skill ROI appears once enough applications and outcomes are logged." />
      ) : (
        <div className="flex flex-col gap-3">
          {skills.map((row, i) => {
            const rank = i + 1;
            const isRecommended = recommended.has(row.skill);
            const isOpen = expanded.has(row.skill);
            return (
              <div
                key={row.skill}
                data-testid={`roi-row-${row.skill}`}
                className={cn(
                  "rounded-2xl border p-3 flex flex-col gap-2",
                  isRecommended
                    ? "bg-[#7e5fff]/[0.06] border-[#7e5fff]/25"
                    : "bg-white/[0.02] border-white/10"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="size-6 font-bold rounded-lg bg-white/6 text-[#a1a1a1] text-[11px] border border-white/10 flex justify-center items-center flex-shrink-0">
                    {rank}
                  </div>
                  <span
                    data-testid="roi-skill"
                    className="font-medium text-neutral-50 text-[13px] truncate"
                  >
                    {row.skill}
                  </span>
                  {isRecommended && (
                    <span className="font-semibold rounded-full bg-[#7e5fff]/15 text-[#7e5fff] text-[10px] border border-[#7e5fff]/25 px-2 py-0.5">
                      Recommended
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-3">
                    <span className="text-[#a1a1a1] text-[11px]">n = {row.n}</span>
                    <span className="font-bold text-neutral-50 text-[13px] tabular-nums">
                      {fmtRoi(row.roi)}
                    </span>
                    <ConfidenceBadge level={row.confidence} />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => toggle(row.skill)}
                  aria-expanded={isOpen}
                  className="self-start flex items-center gap-1 text-[#a1a1a1] hover:text-neutral-200 text-[11px] transition-colors"
                >
                  <ChevronDown
                    className={cn("size-3 transition-transform", isOpen && "rotate-180")}
                  />
                  Why? ({row.contributing_signal_ids.length})
                </button>

                {isOpen && (
                  <div className="pl-4 flex flex-col gap-1">
                    {row.contributing_signal_ids.length > 0 ? (
                      row.contributing_signal_ids.map((id) => (
                        <span
                          key={id}
                          className="font-mono text-[#a1a1a1] text-[11px]"
                        >
                          {id}
                        </span>
                      ))
                    ) : (
                      <span className="text-[#a1a1a1] text-[11px] italic">
                        No contributing signals recorded.
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
