import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sunrise, Briefcase, TrendingUp, FileText, Target, Bell, AlertTriangle, Loader2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { DormantEmptyState } from "@/components/ui/DormantEmptyState";
import { briefingService } from "@/services/briefing";
import type { DailyBriefing } from "@/types/briefing";

/**
 * Phase 15.4 — the daily career briefing on the Dashboard.
 *
 * Composes five sections from the existing engines, aligned to the tracked goal.
 * Recommend-only (ADR-012): every item is a suggestion the user acts on — the
 * actions are internal navigations, never an external submit. Empty sections show
 * the dormant state, never fabricated jobs/gaps (ADR-006).
 */

function Section({
  icon: Icon,
  title,
  empty,
  emptyText,
  children,
}: {
  icon: typeof Briefcase;
  title: string;
  empty: boolean;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/10 p-4">
      <div className="flex items-center gap-2 text-xs font-semibold text-neutral-200 mb-2.5">
        <Icon className="size-4 text-accent" />
        {title}
      </div>
      {empty ? <DormantEmptyState title="Nothing here yet" description={emptyText} /> : <div className="flex flex-col gap-2">{children}</div>}
    </div>
  );
}

export function DailyBriefing() {
  const navigate = useNavigate();
  const [data, setData] = useState<DailyBriefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    briefingService
      .get()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load briefing"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <GlassCard className="p-6 flex items-center justify-center"><Loader2 className="size-5 animate-spin text-accent" /></GlassCard>;
  if (error)
    return (
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 text-sm text-red-400">
          <AlertTriangle className="size-4" /> {error}
        </div>
      </GlassCard>
    );
  if (!data) return null;

  return (
    <GlassCard className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-neutral-200">
          <Sunrise className="size-4 text-accent" />
          Daily Briefing
        </h2>
        {data.goal ? (
          <span className="flex items-center gap-1.5 text-xs text-[var(--fg-muted)]">
            Goal: <span className="text-neutral-300">{data.goal.category}</span>
            <ConfidenceBadge level={data.goal.confidence} />
          </span>
        ) : (
          <span className="text-xs text-[var(--fg-muted)]">No goal set yet — log outcomes to establish one</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Section icon={Briefcase} title="Jobs to apply to" empty={data.jobs_to_apply.length === 0} emptyText="Add applications with a job description to get ranked recommendations.">
          {data.jobs_to_apply.map((j) => (
            <button
              key={j.application_id}
              onClick={() => navigate("/applications")}
              className="text-left rounded-lg bg-white/[0.02] hover:bg-white/[0.05] transition-colors p-2.5"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-neutral-200">{j.position} · {j.company}</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20 capitalize">{j.recommendation}</span>
                <ConfidenceBadge level={j.confidence} />
                {!j.aligned_to_goal && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">off-goal</span>
                )}
              </div>
            </button>
          ))}
        </Section>

        <Section icon={TrendingUp} title="Skill gaps" empty={data.skill_gaps.length === 0} emptyText="Skill gaps appear as you log application outcomes.">
          {data.skill_gaps.map((g) => (
            <div key={g.skill_name} className="text-sm text-neutral-300 flex items-center justify-between">
              <span className="capitalize">{g.skill_name}</span>
              <span className="text-[11px] text-[var(--fg-muted)]">{g.gap_type} · blocks {g.blocking_interviews}</span>
            </div>
          ))}
        </Section>

        <Section icon={FileText} title="Resume adjustments" empty={data.resume_adjustments.length === 0} emptyText="Resume focus appears once you save a job description.">
          {data.resume_adjustments.map((r) => (
            <button key={r.application_id} onClick={() => navigate("/resumes")} className="text-left text-sm text-neutral-300 hover:text-neutral-100 transition-colors">
              {r.company}: <span className="text-accent">{r.template_name}</span>
            </button>
          ))}
        </Section>

        <Section icon={Target} title="ATS opportunities" empty={data.ats_opportunities.length === 0} emptyText="Draft applications with a JD show up here to analyze.">
          {data.ats_opportunities.map((o) => (
            <button key={o.application_id} onClick={() => navigate("/ats")} className="text-left text-sm text-neutral-300 hover:text-neutral-100 transition-colors">
              Review ATS fit · {o.company}
            </button>
          ))}
        </Section>

        <Section icon={Bell} title="Follow-ups needed" empty={data.follow_ups.length === 0} emptyText="Active applications needing a nudge show up here.">
          {data.follow_ups.map((f) => (
            <button key={f.application_id} onClick={() => navigate("/applications")} className="text-left text-sm text-neutral-300 hover:text-neutral-100 transition-colors">
              {f.company} · <span className="text-[var(--fg-muted)] capitalize">{f.status.replace("_", " ")}</span>
            </button>
          ))}
        </Section>
      </div>
    </GlassCard>
  );
}
