import { apiFetch } from "./api";
import type { AnswerEvaluation, GeneratedQuestion, LearningOutcome } from "@/types/api";

export interface TemplateRanking {
  template_name: string;
  avg_ats_score: number | null;
  win_rate: number | null;
  application_count: number;
}

export interface AtsVsOutcome {
  signal_type: string;
  avg_ats_score: number | null;
  count: number;
}

export const learningService = {
  // Used by InterviewPrepPage
  generateQuestions: (req: { application_id: string; job_description: string; persona?: string }) =>
    apiFetch<{ questions: GeneratedQuestion[] }>("/questions/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  recordOutcome: (outcome: LearningOutcome) =>
    apiFetch<{ recorded: boolean }>("/learning/outcome", {
      method: "POST",
      body: JSON.stringify(outcome),
    }),

  // 15.3 — interview simulation deepening. Generate-only (ADR-012).
  getFollowups: (req: { question: string; answer_text: string; persona?: string; max_followups?: number }) =>
    apiFetch<{ followups: string[] }>("/questions/followups", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  evaluateAnswer: (req: { answer_text: string; expected_node_ids?: string[] }) =>
    apiFetch<AnswerEvaluation>("/questions/evaluate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  // Used by LearningPage
  getRankings: () =>
    apiFetch<{ template_rankings: TemplateRanking[] }>("/learning/rankings"),
  getReport: () =>
    apiFetch<{ template_rankings: TemplateRanking[]; ats_vs_outcome: AtsVsOutcome[] }>(
      "/learning/report"
    ),
};
