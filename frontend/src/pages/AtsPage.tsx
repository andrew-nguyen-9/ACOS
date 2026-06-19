import { useState } from "react";
import { BarChart3, RefreshCw, AlertTriangle, Target } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { resumeService } from "@/services/resume";
import type { ResumeGenerateResponse } from "@/types/api";

export default function AtsPage() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeGenerateResponse | null>(null);

  const analyze = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await resumeService.generate({ job_description: jd, template_name: "software" });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const score = result?.ats_score;

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">ATS Analysis</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Score your resume against any job description</p>
      </div>

      <GlassCard className="p-5">
        <label className="block text-sm font-medium text-neutral-200 mb-3">Job Description</label>
        <textarea
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the job description to analyze keyword match…"
          rows={5}
          className="w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
        />
        {error && (
          <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
            <span className="text-red-400 text-xs">{error}</span>
          </div>
        )}
        <button
          onClick={analyze}
          disabled={loading || !jd.trim()}
          className="mt-4 w-full py-3 rounded-xl bg-[#4c8dff] text-white font-semibold text-sm disabled:opacity-40 hover:opacity-90 flex items-center justify-center gap-2 transition-opacity"
        >
          {loading ? <><RefreshCw className="size-4 animate-spin" /> Analyzing…</> : <><BarChart3 className="size-4" /> Analyze Match</>}
        </button>
      </GlassCard>

      {loading && (
        <GlassCard className="p-8 flex items-center justify-center">
          <LoadingSpinner size="lg" label="Analyzing keyword match…" />
        </GlassCard>
      )}

      {score && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Overall Score", value: score.overall_score, color: "#4c8dff" },
            { label: "Keyword Match", value: score.keyword_score, color: "#30D158" },
            { label: "Skills Match", value: score.skill_score, color: "#5AC8FA" },
          ].map(({ label, value, color }) => (
            <GlassCard key={label} className="p-5 text-center">
              <p className="text-[#a1a1a1] text-xs mb-2">{label}</p>
              <div className="relative size-20 mx-auto mb-2">
                <svg viewBox="0 0 36 36" className="size-20 -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="2.5" />
                  <circle
                    cx="18" cy="18" r="15.9"
                    fill="none"
                    stroke={color}
                    strokeWidth="2.5"
                    strokeDasharray={`${value} ${100 - value}`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-bold text-neutral-50 text-lg">{value}</span>
                </div>
              </div>
            </GlassCard>
          ))}
          <GlassCard className="col-span-3 p-5">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs font-medium text-[#30D158] mb-2 flex items-center gap-1">
                  <Target className="size-3.5" /> Matched Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {score.matched_keywords.map((k) => (
                    <span key={k} className="text-xs px-2.5 py-1 rounded-full bg-[#30D158]/10 text-[#30D158] border border-[#30D158]/20">{k}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-[#FF9F0A] mb-2 flex items-center gap-1">
                  <AlertTriangle className="size-3.5" /> Missing Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {score.missing_keywords.map((k) => (
                    <span key={k} className="text-xs px-2.5 py-1 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">{k}</span>
                  ))}
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
