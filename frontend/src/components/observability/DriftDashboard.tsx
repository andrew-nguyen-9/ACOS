import { useEffect, useState } from "react";
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { DormantEmptyState } from "@/components/ui/DormantEmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { observabilityService, type DriftMetric } from "@/services/observability";

/**
 * Phase 14.2 — local drift dashboard over the existing observability series.
 *
 * Surfaces the three brief-named drifts (ATS accuracy, resume success rate,
 * embedding quality) as trend cards. Confidence + low-n handling come straight
 * from the server (ADR-006): a card with no confident figure shows the dormant
 * state, never a fabricated number. No external telemetry — all local.
 *
 * ponytail: self-contained fetch-on-mount (see flywheel.ts); no store until a
 * measured re-fetch problem appears.
 */

// The three drifts the brief names, with human labels + how to read a rise.
const TRACKED: { kind: string; label: string; goodWhenUp: boolean }[] = [
  { kind: "ats_score", label: "ATS accuracy", goodWhenUp: true },
  { kind: "success_rate", label: "Resume success rate", goodWhenUp: true },
  { kind: "embedding_drift", label: "Embedding quality", goodWhenUp: false },
];

function DeltaArrow({ delta }: { delta: number }) {
  if (delta > 0) return <ArrowUpRight className="size-4 text-[#30D158]" />;
  if (delta < 0) return <ArrowDownRight className="size-4 text-[#FF9F0A]" />;
  return <ArrowRight className="size-4 text-[#a1a1a1]" />;
}

function MetricCard({ label, metric }: { label: string; metric: DriftMetric | undefined }) {
  // No confident figure (thin data or absent) → dormant, not a fake trend.
  const dormant = !metric || metric.confidence === null || metric.baseline === null;
  return (
    <div className="rounded-2xl bg-neutral-900 border border-white/10 p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <h3 className="font-medium text-neutral-50 text-[13px] tracking-tight">{label}</h3>
        {metric?.confidence && (
          <span className="ml-auto">
            <ConfidenceBadge level={metric.confidence} />
          </span>
        )}
      </div>
      {dormant ? (
        <DormantEmptyState
          title="Not enough data yet"
          description="A confident drift trend needs more recorded samples."
        />
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            <span className="text-neutral-50 text-2xl font-semibold tabular-nums">
              {metric!.current?.toFixed(2)}
            </span>
            <DeltaArrow delta={metric!.delta ?? 0} />
            <span className="text-[#a1a1a1] text-[12px] tabular-nums">
              from {metric!.baseline?.toFixed(2)}
            </span>
            {metric!.drifting && (
              <span className="ml-auto rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20 text-[10px] px-2 py-0.5">
                drifting
              </span>
            )}
          </div>
          <div className="text-[#6b6b6b] text-[11px]">
            {metric!.samples} samples
            {metric!.baseline_version && ` · baseline v${metric!.baseline_version}`}
          </div>
        </>
      )}
    </div>
  );
}

export function DriftDashboard() {
  const [metrics, setMetrics] = useState<DriftMetric[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    observabilityService
      .getDrift()
      .then((r) => setMetrics(r.metrics))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const byKind = new Map((metrics ?? []).map((m) => [m.kind, m]));

  return (
    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Activity className="size-4 text-[#7e5fff]" />
        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
          Drift &amp; health
        </h2>
        <span className="ml-auto font-medium rounded-full bg-white/6 text-[#a1a1a1] text-[10px] border border-white/10 px-2 py-0.5">
          local-only
        </span>
      </div>
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {TRACKED.map((t) => (
            <MetricCard key={t.kind} label={t.label} metric={byKind.get(t.kind)} />
          ))}
        </div>
      )}
    </div>
  );
}
