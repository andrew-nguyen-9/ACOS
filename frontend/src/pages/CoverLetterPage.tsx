import { useState } from "react";
import { Mail, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { coverLetterService } from "@/services/coverLetter";

interface Result {
  cover_letter_id: string;
  content_text: string;
  weak_inference_count: number;
  requires_approval: boolean;
}

export default function CoverLetterPage() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  const generate = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await coverLetterService.generate({ job_description: jd });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Cover Letter Builder</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Tailored to the job — grounded in your evidence</p>
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-6 flex-1">
        <GlassCard className="p-5 flex flex-col">
          <label className="block text-sm font-medium text-neutral-200 mb-3">Job Description</label>
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the job description…"
            className="flex-1 w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors min-h-[280px]"
          />
          {error && (
            <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
              <span className="text-red-400 text-xs">{error}</span>
            </div>
          )}
          <button
            onClick={generate}
            disabled={loading || !jd.trim()}
            className="mt-4 w-full py-3 rounded-xl bg-[#4c8dff] text-white font-semibold text-sm transition-opacity disabled:opacity-40 hover:opacity-90 flex items-center justify-center gap-2"
          >
            {loading ? <><RefreshCw className="size-4 animate-spin" /> Generating…</> : <><Mail className="size-4" /> Generate Cover Letter</>}
          </button>
        </GlassCard>

        <div className="flex flex-col gap-4">
          {!result && !loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Mail className="size-8 text-neutral-600 mx-auto mb-3" />
                <p className="text-[#a1a1a1] text-sm">Your cover letter will appear here</p>
              </div>
            </GlassCard>
          )}
          {loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <LoadingSpinner size="lg" label="Writing your cover letter…" />
            </GlassCard>
          )}
          {result && (
            <GlassCard className="p-5 flex-1 overflow-auto">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-[#30D158]" />
                  <span className="font-medium text-neutral-200 text-sm">Cover Letter</span>
                </div>
                {result.requires_approval && (
                  <ConfidenceBadge level="weak_inference" />
                )}
              </div>
              <div className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                {result.content_text}
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
}
