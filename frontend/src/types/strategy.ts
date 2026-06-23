/**
 * Phase 15.1 — types for the job-prioritization surface.
 *
 * Mirrors backend/models/strategy.py `ApplicationPriority` + `PrioritizeRequest`.
 * The engine ranks server-side (ADR-012); the client renders that order verbatim.
 */
import type { ConfidenceLevel } from "./api";

export type JobPriorityAction = "prioritize" | "tailor" | "bridge" | "skip";

export interface PrioritizeJob {
  job_id: string;
  jd_text: string;
}

export interface ApplicationPriority {
  job_id: string;
  jd_snippet: string;
  priority: JobPriorityAction;
  reason: string;
  /** Fit estimate 0–100 — an estimate, always shown with its confidence. */
  fit_score: number;
  confidence: ConfidenceLevel;
  missing_critical_skills: string[];
  risk_factors: string[];
  explanation: string;
  /** Server-decided; weak_inference rows are never marked (ADR-012 trap 3). */
  top_pick: boolean;
}

/** 15.2 — composed per-application suggestion. Mirrors models/strategy.py. */
export interface ApplicationSuggestion {
  recommendation: "apply" | "tailor" | "skip";
  reason: string;
  fit_score: number;
  confidence: ConfidenceLevel;
  missing_critical_skills: string[];
  risk_factors: string[];
  explanation: string;
  resume_template: string;
  resume_reason: string;
  cover_letter_tone: number;
  cover_letter_tone_descriptor: string;
  interview_probability: number;
  interview_sample_size: number;
  interview_confidence: ConfidenceLevel;
  interview_category: string;
}
