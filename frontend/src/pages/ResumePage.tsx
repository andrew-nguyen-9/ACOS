import { useState } from "react";
import {
  FileText, Shield, CheckCircle2, AlertTriangle, Download, RefreshCw,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { EvidencePanel, type EvidenceItem } from "@/components/shared/EvidencePanel";
import { BulletXRay } from "@/components/resume/BulletXRay";
import { resumeService } from "@/services/resume";
import * as haptics from "@/lib/haptics";
import type { ResumeGenerateResponse } from "@/types/api";

const TEMPLATES = [
  { id: "software", label: "Software Engineer" },
  { id: "ai", label: "AI / ML" },
  { id: "product", label: "Product Manager" },
  { id: "consulting", label: "Consulting" },
  { id: "data_analytics", label: "Data Analytics" },
  { id: "healthcare", label: "Healthcare" },
];

export default function ResumePage() {
  const [jd, setJd] = useState("");
  const [template, setTemplate] = useState("software");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeGenerateResponse | null>(null);

  const generate = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await resumeService.generate({ job_description: jd, template_name: template });
      setResult(res);
      haptics.success();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
      haptics.warn();
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = async () => {
    if (!result) return;
    try {
      const blob = await resumeService.exportDocx({ job_description: jd, template_name: template });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed");
    }
  };

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Resume Builder</h1>
          <p className="text-[#a1a1a1] text-sm mt-1">AI-generated from your verified evidence</p>
        </div>
        {result && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#30D158]/10 border border-[#30D158]/20">
            <Shield className="size-3.5 text-[#30D158]" />
            <span className="text-[#30D158] text-xs font-medium">Hallucination Prevention Active</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-[1fr_1fr_280px] gap-6 flex-1">
        <div className="flex flex-col gap-4">
          <GlassCard className="p-5">
            <label className="block text-sm font-medium text-neutral-200 mb-3">Template</label>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTemplate(t.id)}
                  className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left ${
                    template === t.id
                      ? "bg-[#4c8dff]/20 text-[#4c8dff] border border-[#4c8dff]/30"
                      : "bg-white/[0.04] text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.08] border border-transparent"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-5 flex-1 flex flex-col">
            <label className="block text-sm font-medium text-neutral-200 mb-3">
              Job Description
            </label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description here…"
              className="flex-1 w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors min-h-[200px]"
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
              {loading ? (
                <>
                  <RefreshCw className="size-4 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <FileText className="size-4" />
                  Generate Resume
                </>
              )}
            </button>
          </GlassCard>
        </div>

        <div className="flex flex-col gap-4">
          {!result && !loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="size-8 text-neutral-600 mx-auto mb-3" />
                <p className="text-[#a1a1a1] text-sm">Your generated resume will appear here</p>
              </div>
            </GlassCard>
          )}
          {loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <LoadingSpinner size="lg" label="Generating your resume…" />
            </GlassCard>
          )}
          {result && (
            <>
              <GlassCard className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-4 text-[#30D158]" />
                    <span className="font-medium text-neutral-200 text-sm">Generated Resume</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {result.requires_approval && (
                      <span className="text-xs px-2 py-1 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">
                        {result.weak_inference_count} needs review
                      </span>
                    )}
                    <span className="text-xs px-2 py-1 rounded-full bg-[#4c8dff]/10 text-[#4c8dff] border border-[#4c8dff]/20">
                      ATS {result.ats_score.overall_score}
                    </span>
                    <button
                      onClick={downloadDocx}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.08] text-neutral-200 text-xs font-medium hover:bg-white/[0.12] transition-colors"
                    >
                      <Download className="size-3.5" />
                      .docx
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-4 max-h-80 overflow-auto pr-2">
                  {result.content_json.experiences.map((exp, i) => (
                    <div key={i}>
                      <div className="flex items-baseline justify-between">
                        <p className="font-semibold text-neutral-100 text-sm">{exp.title} — {exp.company}</p>
                        <p className="text-[#a1a1a1] text-xs">{exp.dates}</p>
                      </div>
                      <ul className="mt-2 flex flex-col gap-1.5">
                        {exp.bullets.map((b, j) => (
                          <li key={j} className="flex items-start gap-2 text-sm text-neutral-300">
                            <span className="mt-1.5 size-1.5 rounded-full bg-[#4c8dff] flex-shrink-0" />
                            <BulletXRay
                              text={b.text}
                              confidence={b.confidence}
                              matchedKeywords={result.ats_score.matched_keywords}
                            >
                              <span className="cursor-help underline decoration-dotted decoration-white/20 underline-offset-4">
                                {b.text}
                              </span>
                            </BulletXRay>
                            <ConfidenceBadge level={b.confidence} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </GlassCard>
              {result.content_json.skills.length > 0 && (
                <GlassCard className="p-4">
                  <p className="text-xs font-medium text-[#a1a1a1] mb-2">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {result.content_json.skills.map((s) => (
                      <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-neutral-300 border border-white/10">
                        {s}
                      </span>
                    ))}
                  </div>
                </GlassCard>
              )}
            </>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <EvidencePanel
            items={
              result
                ? result.content_json.experiences.flatMap((exp) =>
                    exp.bullets.map((b): EvidenceItem => ({
                      id: b.evidence_id,
                      text: b.text,
                      confidence: b.confidence,
                    }))
                  )
                : []
            }
          />
        </div>
      </div>
    </div>
  );
}
