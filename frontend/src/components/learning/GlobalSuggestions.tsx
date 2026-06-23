import { useEffect, useState } from "react";
import { Globe } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { DormantEmptyState } from "@/components/ui/DormantEmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { fmtRoi } from "@/lib/utils";
import { flywheelService } from "@/services/flywheel";
import type { GlobalRoiResponse } from "@/types/flywheel";

/**
 * Phase 13.3 — surfaces GET /flywheel/global/roi inside the Learning Engine.
 *
 * Cross-tenant patterns rendered as SUGGESTIONS, never directives (ADR-009):
 * global informs, local decides. Render order = the server's ranking (never
 * re-sorted). Each row carries only the route's allowlisted aggregate fields —
 * `tenant_count` is a COUNT, never tenant ids, so nothing here can re-identify a
 * contributor. Under k-anonymity (k<5) the route returns `rankings: []`; that is
 * the dormant-by-design state today, not an error.
 */
// ponytail: self-contained fetch — request-per-view is fine (see flywheel.ts),
// matches SkillRoiSection; no shared store until a measured re-fetch problem.
export function GlobalSuggestions() {
  const [data, setData] = useState<GlobalRoiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    flywheelService
      .getGlobalRoi()
      .then(setData)
      .catch((e) => {
        // A real fetch failure is NOT k-anonymity dormancy — keep them distinct
        // so a server outage never masquerades as the privacy floor.
        console.error(e);
        setFailed(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const rankings = data?.rankings ?? [];

  return (
    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Globe className="size-4 text-[#5AC8FA]" />
        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
          Global Patterns
        </h2>
        {data?.metric && (
          <span className="ml-auto font-medium rounded-full bg-white/6 text-[#a1a1a1] text-[10px] border border-white/10 px-2 py-0.5">
            {data.metric}
          </span>
        )}
      </div>

      {/* Framing (ADR-009): these are suggestions to weigh against your own
          results, never a rule. Global suggests; local decides. */}
      <p className="text-[#a1a1a1] text-[12px] leading-relaxed">
        Patterns across other ACOS users — consider these against your own
        outcomes, never as a rule.
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner label="Loading global patterns…" />
        </div>
      ) : failed ? (
        <p
          data-testid="global-error"
          className="text-amber-300/90 text-[12px] leading-relaxed"
        >
          Couldn’t load global patterns. This is a temporary error — try again
          shortly.
        </p>
      ) : rankings.length === 0 ? (
        <DormantEmptyState description="Cross-tenant patterns appear once at least five profiles share enough signals (privacy floor)." />
      ) : (
        <div className="flex flex-col gap-3">
          {rankings.map((row) => {
            const tenants = `${row.tenant_count} tenant${row.tenant_count === 1 ? "" : "s"}`;
            // Rows are keyed (industry, skill): the same skill can repeat across
            // industries, so skill alone would collide.
            const rowKey = `${row.industry}-${row.skill}`;
            return (
              <div
                key={rowKey}
                data-testid={`global-row-${rowKey}`}
                className="rounded-2xl border border-white/10 bg-white/[0.02] p-3 flex items-center gap-3"
              >
                <span
                  data-testid="global-skill"
                  className="font-medium text-neutral-50 text-[13px] truncate"
                >
                  {row.skill}
                </span>
                <span className="text-[#a1a1a1] text-[11px] truncate">{row.industry}</span>
                <div className="ml-auto flex items-center gap-3 flex-shrink-0">
                  <span className="text-[#a1a1a1] text-[11px]" title="contributing tenants (count only)">
                    {tenants}
                  </span>
                  <span className="font-bold text-neutral-50 text-[13px] tabular-nums">
                    {fmtRoi(row.roi)}
                  </span>
                  <ConfidenceBadge level={row.confidence} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
