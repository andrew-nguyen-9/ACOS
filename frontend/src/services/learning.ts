import { apiFetch } from "./api";
import type { GeneratedQuestion, LearningOutcome } from "@/types/api";

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
  generateQuestions: (applicationId: string) =>
    apiFetch<{ questions: GeneratedQuestion[] }>(
      `/questions/generate?application_id=${applicationId}`,
      { method: "POST" }
    ),
  recordOutcome: (outcome: LearningOutcome) =>
    apiFetch<{ recorded: boolean }>("/learning/outcome", {
      method: "POST",
      body: JSON.stringify(outcome),
    }),

  // Used by LearningPage
  getRankings: () =>
    apiFetch<{ template_rankings: TemplateRanking[] }>("/learning/rankings"),
  getReport: () =>
    apiFetch<{ template_rankings: TemplateRanking[]; ats_vs_outcome: AtsVsOutcome[] }>(
      "/learning/report"
    ),
};
