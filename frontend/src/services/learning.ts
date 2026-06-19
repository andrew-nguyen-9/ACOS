import { apiFetch } from "./api";
import type { GeneratedQuestion, LearningOutcome } from "@/types/api";

export const learningService = {
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
  getRecommendations: () =>
    apiFetch<{ recommendations: GeneratedQuestion[] }>("/learning/recommendations"),
};
