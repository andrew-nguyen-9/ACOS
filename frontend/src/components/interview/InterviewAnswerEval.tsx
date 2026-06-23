import { useState } from "react";
import { Sparkles, Loader2, AlertTriangle } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { learningService } from "@/services/learning";
import type { AnswerEvaluation } from "@/types/api";

/**
 * Phase 15.3 — type an answer, get a KG-grounded evaluation + recruiter follow-ups.
 *
 * The score is never bare: it shows which knowledge-graph evidence the answer
 * covered (and what it missed), tagged with confidence (ADR-006). The recruiter
 * is simulated locally — generate-only, no external action (ADR-012).
 */
export function InterviewAnswerEval({
  questionText,
  persona = "balanced",
}: {
  questionText: string;
  persona?: string;
}) {
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);
  const [followups, setFollowups] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!answer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const [ev, fu] = await Promise.all([
        learningService.evaluateAnswer({ answer_text: answer }),
        learningService.getFollowups({ question: questionText, answer_text: answer, persona }),
      ]);
      setEvaluation(ev);
      setFollowups(fu.followups);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to evaluate answer");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 flex flex-col gap-3">
      <label className="text-xs font-medium text-[#a1a1a1]">Your answer</label>
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer to practice…"
        className="w-full h-24 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors resize-none"
      />
      <button
        onClick={run}
        disabled={busy || !answer.trim()}
        className="self-start flex items-center gap-2 px-4 py-2 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
      >
        {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
        Evaluate &amp; get follow-ups
      </button>

      {error && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {evaluation && (
        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-neutral-200">
              Evidence coverage {Math.round(evaluation.coverage * 100)}%
            </span>
            <ConfidenceBadge level={evaluation.confidence} />
          </div>
          {evaluation.expected_count === 0 ? (
            <p className="text-xs text-[#a1a1a1]">
              No knowledge-graph evidence to ground against yet — add experience and skills to get a grounded score.
            </p>
          ) : (
            <>
              {evaluation.matched_labels.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[11px] text-[#a1a1a1]">Covered:</span>
                  {evaluation.matched_labels.map((l) => (
                    <span key={l} className="text-[11px] px-2 py-0.5 rounded-full bg-[#30D158]/10 text-[#30D158] border border-[#30D158]/20">
                      {l}
                    </span>
                  ))}
                </div>
              )}
              <p className="text-xs text-[#a1a1a1]">
                {evaluation.missing_node_ids.length} relevant evidence item
                {evaluation.missing_node_ids.length === 1 ? "" : "s"} not yet referenced.
              </p>
            </>
          )}
        </div>
      )}

      {followups.length > 0 && (
        <div className="rounded-xl bg-[#4c8dff]/[0.06] border border-[#4c8dff]/20 p-4">
          <p className="text-xs font-medium text-[#4c8dff] mb-2">Recruiter follow-ups</p>
          <ul className="flex flex-col gap-1.5">
            {followups.map((f, i) => (
              <li key={i} className="text-sm text-neutral-300">• {f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
