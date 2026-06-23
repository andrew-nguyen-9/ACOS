import { useEffect, useState } from "react";
import { FileText, Mail, MessageSquareMore, AlertTriangle, Loader2 } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { strategyService } from "@/services/strategy";
import { applicationsService } from "@/services/applications";
import type { Application } from "@/types/api";
import type { ApplicationSuggestion as Suggestion } from "@/types/strategy";

/**
 * Phase 15.2 — per-application Apply/Skip/Tailor suggestion.
 *
 * Recommend-only (ADR-012): this card surfaces a recommendation + the resume
 * version, cover-letter tone, and interview outlook behind it — each explained
 * and confidence-tagged. The action buttons are INTERNAL: "Mark as applied"
 * flips the local CRM status; "Tailor in Resume Builder" opens the in-app flow.
 * There is no button that submits to a job board (see the test).
 */

const REC: Record<Suggestion["recommendation"], { label: string; className: string }> = {
  apply: { label: "Apply", className: "bg-[#30D158]/10 text-[#30D158] border-[#30D158]/20" },
  tailor: { label: "Tailor first", className: "bg-[#4c8dff]/10 text-[#4c8dff] border-[#4c8dff]/20" },
  skip: { label: "Skip", className: "bg-white/[0.06] text-[#a1a1a1] border-white/10" },
};

function Section({ icon: Icon, title, children }: { icon: typeof FileText; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-[#a1a1a1] mb-1.5">
        <Icon className="size-3.5" />
        {title}
      </div>
      {children}
    </div>
  );
}

export function ApplicationSuggestion({
  app,
  onApplied,
  onTailor,
}: {
  app: Application;
  onApplied?: (updated: Application) => void;
  onTailor?: () => void;
}) {
  const [data, setData] = useState<Suggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  const jd = app.job_description?.trim();

  useEffect(() => {
    if (!jd) return;
    setLoading(true);
    setError(null);
    strategyService
      .suggest(jd)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load suggestion"))
      .finally(() => setLoading(false));
  }, [jd]);

  if (!jd) {
    return (
      <p className="text-sm text-[#a1a1a1]">
        Add a job description to this application to get a tailored Apply / Skip / Tailor recommendation.
      </p>
    );
  }

  if (loading) return <Loader2 className="size-5 animate-spin text-[#4c8dff]" />;
  if (error)
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
        <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  if (!data) return null;

  const rec = REC[data.recommendation];

  const markApplied = async () => {
    setApplying(true);
    try {
      const updated = await applicationsService.update(app.id, { status: "applied" });
      onApplied?.(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`text-sm px-3 py-1 rounded-full border font-semibold ${rec.className}`}>{rec.label}</span>
        <ConfidenceBadge level={data.confidence} />
        <span className="text-xs text-[#a1a1a1]">Fit estimate {data.fit_score}/100</span>
      </div>
      <p className="text-sm text-neutral-300">{data.reason}</p>

      <Section icon={FileText} title="Recommended resume">
        <p className="text-sm text-neutral-200">{data.resume_template}</p>
        <p className="text-xs text-[#a1a1a1] mt-0.5">{data.resume_reason}</p>
      </Section>

      <Section icon={Mail} title="Cover-letter tone">
        <p className="text-sm text-neutral-200">{data.cover_letter_tone_descriptor}</p>
      </Section>

      <Section icon={MessageSquareMore} title="Interview outlook">
        <div className="flex items-center gap-2">
          <p className="text-sm text-neutral-200">
            {Math.round(data.interview_probability * 100)}% interview likelihood
          </p>
          <ConfidenceBadge level={data.interview_confidence} />
        </div>
        <p className="text-xs text-[#a1a1a1] mt-0.5">
          {data.interview_category} · based on {data.interview_sample_size} past signal
          {data.interview_sample_size === 1 ? "" : "s"}
        </p>
      </Section>

      {data.missing_critical_skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-[11px] text-[#a1a1a1]">Gaps:</span>
          {data.missing_critical_skills.map((s) => (
            <span key={s} className="text-[11px] px-2 py-0.5 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Internal-only actions (ADR-012): no external submit. */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={onTailor}
          className="flex-1 py-2 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Tailor in Resume Builder
        </button>
        <button
          onClick={markApplied}
          disabled={applying || app.status === "applied"}
          className="flex-1 py-2 rounded-xl bg-white/[0.06] text-neutral-200 text-sm font-medium disabled:opacity-40 hover:bg-white/[0.1] transition-colors"
        >
          {app.status === "applied" ? "Marked applied" : applying ? "Saving…" : "Mark as applied"}
        </button>
      </div>
    </div>
  );
}
