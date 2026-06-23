/**
 * Phase 15.1 — typed client for the strategy job-prioritization route.
 *
 * Thin wrapper over apiFetch (no new HTTP client). The agent surface is
 * read/rank only — there is no submit/contact method here, by design (ADR-012).
 */
import { apiFetch } from "./api";
import type {
  ApplicationPriority,
  ApplicationSuggestion,
  PrioritizeJob,
} from "@/types/strategy";

export const strategyService = {
  // POST, not GET: pasted JDs can be many KB — a query param would hit the URL
  // limit (414). The body carries them (matches routes/strategy.py).
  prioritize: (jobs: PrioritizeJob[]) =>
    apiFetch<ApplicationPriority[]>("/strategy/prioritize", {
      method: "POST",
      body: JSON.stringify({ jobs }),
    }),

  suggest: (jd_text: string) =>
    apiFetch<ApplicationSuggestion>("/strategy/suggestion", {
      method: "POST",
      body: JSON.stringify({ jd_text }),
    }),
};
