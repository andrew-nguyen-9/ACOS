/**
 * Phase 15.4 — daily briefing shape. Mirrors backend/services/briefing/service.py.
 * Recommend-only (ADR-012): the briefing surfaces what to do; the user acts.
 */
import type { ConfidenceLevel } from "./api";

export interface BriefingGoal {
  category: string;
  interview_probability: number;
  confidence: ConfidenceLevel;
  sample_size: number;
}

export interface BriefingJob {
  application_id: string;
  company: string;
  position: string;
  recommendation: "apply" | "tailor";
  fit_score: number;
  confidence: ConfidenceLevel;
  category: string;
  aligned_to_goal: boolean;
}

export interface BriefingSkillGap {
  skill_name: string;
  gap_type: string;
  frequency: number;
  blocking_interviews: number;
  expected_lift_per_hour: number;
  priority_rank: number;
}

export interface BriefingResumeAdjustment {
  application_id: string;
  company: string;
  template_name: string;
  reason: string;
}

export interface BriefingAtsOpportunity {
  application_id: string;
  company: string;
  position: string;
}

export interface BriefingFollowUp {
  application_id: string;
  company: string;
  position: string;
  status: string;
}

export interface DailyBriefing {
  generated_at: string;
  goal: BriefingGoal | null;
  jobs_to_apply: BriefingJob[];
  skill_gaps: BriefingSkillGap[];
  resume_adjustments: BriefingResumeAdjustment[];
  ats_opportunities: BriefingAtsOpportunity[];
  follow_ups: BriefingFollowUp[];
}
