import { useState, useEffect } from "react";
import { MessageSquareMore, RefreshCw, CheckCircle2, XCircle, SkipForward } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { learningService } from "@/services/learning";
import { applicationsService } from "@/services/applications";
import type { GeneratedQuestion, Application } from "@/types/api";

export default function InterviewPrepPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    applicationsService.list().then(setApplications).catch(console.error);
  }, []);

  const generateQuestions = async () => {
    if (!selectedAppId) return;
    setGenerating(true);
    try {
      const res = await learningService.generateQuestions(selectedAppId);
      setQuestions(res.questions ?? []);
      setCurrentIdx(0);
      setShowAnswer(false);
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const recordOutcome = async (outcome: "correct" | "incorrect" | "skipped") => {
    const q = questions[currentIdx];
    if (!q) return;
    setLoading(true);
    try {
      await learningService.recordOutcome({
        question_id: q.id,
        application_id: q.application_id,
        outcome,
      });
    } catch {
      // best-effort
    } finally {
      setLoading(false);
    }
    setShowAnswer(false);
    setCurrentIdx((i) => i + 1);
  };

  const current = questions[currentIdx];
  const done = currentIdx >= questions.length && questions.length > 0;

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Interview Prep</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Practice questions generated from your applications</p>
      </div>

      <GlassCard className="p-5">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-[#a1a1a1] mb-1.5">Application</label>
            <select
              value={selectedAppId}
              onChange={(e) => setSelectedAppId(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
            >
              <option value="">Select application…</option>
              {applications.map((a) => (
                <option key={a.id} value={a.id}>{a.role} at {a.company}</option>
              ))}
            </select>
          </div>
          <button
            onClick={generateQuestions}
            disabled={generating || !selectedAppId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {generating ? <><RefreshCw className="size-4 animate-spin" /> Generating…</> : <><MessageSquareMore className="size-4" /> Generate Questions</>}
          </button>
        </div>
      </GlassCard>

      {questions.length === 0 && !generating && (
        <GlassCard className="flex-1">
          <EmptyState
            icon={MessageSquareMore}
            title="No questions yet"
            description="Select an application and generate questions to start practicing."
          />
        </GlassCard>
      )}

      {generating && (
        <GlassCard className="flex-1 flex items-center justify-center">
          <LoadingSpinner size="lg" label="Generating interview questions…" />
        </GlassCard>
      )}

      {done && (
        <GlassCard className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <CheckCircle2 className="size-12 text-[#30D158] mx-auto mb-4" />
            <p className="font-semibold text-neutral-50 text-lg">Session Complete!</p>
            <p className="text-[#a1a1a1] text-sm mt-1">You've answered all {questions.length} questions.</p>
            <button
              onClick={() => { setCurrentIdx(0); setShowAnswer(false); }}
              className="mt-4 px-4 py-2 rounded-xl bg-[#4c8dff] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Restart
            </button>
          </div>
        </GlassCard>
      )}

      {current && !done && (
        <div className="flex flex-col gap-4 flex-1">
          <div className="flex items-center justify-between">
            <span className="text-[#a1a1a1] text-sm">{currentIdx + 1} / {questions.length}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-[#a1a1a1] border border-white/10">{current.difficulty}</span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-[#a1a1a1] border border-white/10">{current.question_type}</span>
            </div>
          </div>

          <GlassCard className="p-6 flex-1">
            <p className="font-semibold text-neutral-50 text-lg leading-relaxed">{current.question_text}</p>
            {showAnswer && (
              <div className="mt-6 p-4 rounded-xl bg-[#4c8dff]/[0.08] border border-[#4c8dff]/20">
                <p className="text-xs font-medium text-[#4c8dff] mb-2">Suggested structure</p>
                <p className="text-neutral-300 text-sm">Use the STAR method: Situation → Task → Action → Result. Focus on specific metrics and outcomes from your experience.</p>
              </div>
            )}
            {!showAnswer && (
              <button
                onClick={() => setShowAnswer(true)}
                className="mt-6 px-4 py-2 rounded-xl bg-white/[0.08] text-neutral-300 text-sm hover:bg-white/[0.12] transition-colors"
              >
                Show guidance
              </button>
            )}
          </GlassCard>

          <div className="flex gap-3">
            <button
              onClick={() => recordOutcome("incorrect")}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-colors flex items-center justify-center gap-2"
            >
              <XCircle className="size-4" /> Missed
            </button>
            <button
              onClick={() => recordOutcome("skipped")}
              disabled={loading}
              className="px-5 py-3 rounded-xl bg-white/[0.06] border border-white/10 text-[#a1a1a1] text-sm font-medium hover:bg-white/[0.1] transition-colors flex items-center gap-2"
            >
              <SkipForward className="size-4" /> Skip
            </button>
            <button
              onClick={() => recordOutcome("correct")}
              disabled={loading}
              className="flex-1 py-3 rounded-xl bg-[#30D158]/10 border border-[#30D158]/20 text-[#30D158] text-sm font-medium hover:bg-[#30D158]/20 transition-colors flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="size-4" /> Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
