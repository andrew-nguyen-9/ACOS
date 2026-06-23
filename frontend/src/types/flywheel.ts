/**
 * Phase 13.0 — flywheel route types.
 *
 * Mirrors backend/api/v1/routes/flywheel.py exactly (no invented fields). The
 * `confidence` fields follow ADR-006; the ROI engine only ever emits
 * strong/weak_inference (a correlation is never `verified`), but the shared
 * ConfidenceLevel is a safe superset the badge already renders.
 */
import type { ConfidenceLevel } from "./api";

export type FlywheelMetric = "interview_lift" | "offer_probability" | "ats_delta";

/** One skill's per-tenant ROI (skill_roi.rank_skills). */
export interface SkillRoi {
  skill: string;
  roi: number;
  n: number;
  confidence: ConfidenceLevel;
  contributing_signal_ids: string[];
}

/** GET /flywheel/skills/roi */
export interface SkillRoiResponse {
  metric: string;
  min_n: number;
  skills: SkillRoi[];
  recommended: string[];
}

/** POST /flywheel/strategy — asdict(StrategyRecommendation). JD travels in the body (414-safe). */
export interface StrategyRecommendation {
  industry: string;
  section_order: string[];
  recommended_skills: string[];
  keyword_targets: string[];
  confidence: ConfidenceLevel;
  flagged: boolean;
  evidence: string[];
  global_suggestions: string[];
  notes: string;
}

/** One row of the cross-tenant aggregate (global_patterns.global_skill_roi). */
export interface GlobalRoi {
  industry: string;
  skill: string;
  roi: number;
  tenant_count: number;
  confidence: ConfidenceLevel;
}

/** GET /flywheel/global/roi. `rankings` is empty when k-anonymity (ADR-009)
 *  suppresses every candidate — a normal dormant state, never an error. */
export interface GlobalRoiResponse {
  metric: string;
  rankings: GlobalRoi[];
}

/** _version_dict — the PromptVersion row returned by propose/promote/rollback. */
export interface PromptVersion {
  id: string;
  prompt_name: string;
  version: string;
  is_active: boolean;
  parent_version: string | null;
  change_rationale: string | null;
}

/** POST /flywheel/prompt/trial result. */
export interface TrialResult {
  experiment_id: string;
  name: string;
  status: string;
}

// --- request bodies (mirror the Pydantic models; optional = has a server default) ---

export interface ProposeRequest {
  prompt_name: string;
  proposed_content: string;
  signal_ids: string[];
  rationale: string;
  expected_impact: string;
  confidence_level?: ConfidenceLevel;
  risk_level?: string;
}

export interface TrialRequest {
  prompt_name: string;
  version: string;
}

export interface PromoteRequest {
  prompt_name: string;
  version: string;
  approved_by: string;
}

export interface RollbackRequest {
  prompt_name: string;
  approved_by?: string;
}
