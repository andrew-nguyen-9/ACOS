import { useState } from "react";
import { ListChecks, Loader2, AlertTriangle, Star } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { DormantEmptyState } from "@/components/ui/DormantEmptyState";
import { strategyService } from "@/services/strategy";
import type { ApplicationPriority, JobPriorityAction } from "@/types/strategy";

/**
 * Phase 15.1 — paste/select JDs → server-ranked, explained, confidence-tagged
 * prioritization (ADR-012). This surface RECOMMENDS only: it ranks and explains.
 * There is deliberately no Apply/Contact button that hits an external system —
 * the boundary is enforced by absence (see JobPrioritization.test.tsx).
 */

const ACTION: Record<JobPriorityAction, { label: string; className: string }> = {
  prioritize: { label: "Prioritize", className: "bg-[#30D158]/10 text-[#30D158] border-[#30D158]/20" },
  tailor: { label: "Tailor first", className: "bg-[#4c8dff]/10 text-[#4c8dff] border-[#4c8dff]/20" },
  bridge: { label: "Bridge gaps", className: "bg-[#FF9F0A]/10 text-[#FF9F0A] border-[#FF9F0A]/20" },
  skip: { label: "Skip", className: "bg-white/[0.06] text-[#a1a1a1] border-white/10" },
};

const DELIM = /\n-{3,}\n/; // paste multiple JDs separated by a line of ---

function PriorityRow({ row }: { row: ApplicationPriority }) {
  const action = ACTION[row.priority] ?? ACTION.skip;
  // weak_inference rows are de-emphasized — thin evidence, never a hard nudge.
  const weak = row.confidence === "weak_inference";
  return (
    <GlassCard className={`mb-2 p-4 ${weak ? "opacity-60" : ""} ${row.top_pick ? "ring-1 ring-[#30D158]/40" : ""}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          {row.top_pick && (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-[#30D158]">
              <Star className="size-3 fill-current" /> Top pick
            </span>
          )}
          <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${action.className}`}>
            {action.label}
          </span>
          <ConfidenceBadge level={row.confidence} />
        </div>
        <span className="text-xs text-[#a1a1a1] flex-shrink-0">
          Fit estimate {row.fit_score}/100
        </span>
      </div>
      <p className="text-sm text-neutral-300 mt-2">{row.reason}</p>
      <p className="text-xs text-[#a1a1a1] mt-1">{row.explanation}</p>
      {row.missing_critical_skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          <span className="text-[11px] text-[#a1a1a1]">Missing:</span>
          {row.missing_critical_skills.map((s) => (
            <span key={s} className="text-[11px] px-2 py-0.5 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">
              {s}
            </span>
          ))}
        </div>
      )}
    </GlassCard>
  );
}

export function JobPrioritization({ savedJds = [] }: { savedJds?: string[] }) {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<ApplicationPriority[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const chunks = text.split(DELIM).map((s) => s.trim()).filter(Boolean);
    if (!chunks.length) return;
    const jobs = chunks.map((jd, i) => ({ job_id: `job-${i + 1}`, jd_text: jd }));
    setLoading(true);
    setError(null);
    try {
      // Render the engine's order verbatim — no client-side re-rank (ADR-012).
      setRows(await strategyService.prioritize(jobs));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to prioritize");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm text-neutral-200">
        <ListChecks className="size-4 text-[#4c8dff]" />
        <span className="font-medium">Prioritize jobs</span>
        <span className="text-[#a1a1a1] text-xs">
          — paste one or more JDs (separate with a line of <code>---</code>); ranked by fit, recommend-only
        </span>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste a job description…"
        className="w-full h-28 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors resize-none"
      />
      <div className="flex items-center gap-2">
        <button
          onClick={run}
          disabled={loading || !text.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : <ListChecks className="size-4" />}
          Prioritize
        </button>
        {savedJds.length > 0 && (
          <button
            onClick={() => setText(savedJds.join("\n---\n"))}
            className="px-4 py-2 rounded-xl bg-white/[0.06] text-[#a1a1a1] text-sm hover:bg-white/[0.1] transition-colors"
          >
            Load {savedJds.length} saved JD{savedJds.length > 1 ? "s" : ""}
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {rows !== null &&
        (rows.length === 0 ? (
          <DormantEmptyState title="Nothing to rank" description="Paste a job description above to get a ranked recommendation." />
        ) : (
          <div>{rows.map((r) => <PriorityRow key={r.job_id} row={r} />)}</div>
        ))}
    </div>
  );
}
