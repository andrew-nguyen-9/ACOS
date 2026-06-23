/**
 * Phase 13.0 — typed client for the read/write flywheel routes.
 *
 * Thin wrappers over apiFetch, mirroring backend/api/v1/routes/flywheel.py. No
 * cache layer here: the consuming pages (13.1+) fetch on mount and the data is
 * batch-recomputed off the hot path, so a request-per-view is fine.
 * ponytail: add memoization only if a measured re-fetch problem shows up.
 */
import { apiFetch } from "./api";
import type {
  GlobalRoiResponse,
  ProposeRequest,
  PromoteRequest,
  PromptVersion,
  RollbackRequest,
  SkillRoiResponse,
  StrategyRecommendation,
  TrialRequest,
  TrialResult,
} from "@/types/flywheel";

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

function post<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export const flywheelService = {
  getSkillRoi: (opts: { metric?: string; min_n?: number } = {}) =>
    apiFetch<SkillRoiResponse>(`/flywheel/skills/roi${qs(opts)}`),

  // POST, not GET: a pasted JD can be many KB — as a query param it would blow
  // the URL/header limit (414). The body carries it (matches routes/flywheel.py).
  getStrategy: (target_jd: string) =>
    post<StrategyRecommendation>("/flywheel/strategy", { target_jd }),

  getGlobalRoi: (opts: { metric?: string } = {}) =>
    apiFetch<GlobalRoiResponse>(`/flywheel/global/roi${qs(opts)}`),

  proposePrompt: (body: ProposeRequest) =>
    post<PromptVersion>("/flywheel/prompt/propose", body),

  trialPrompt: (body: TrialRequest) =>
    post<TrialResult>("/flywheel/prompt/trial", body),

  promotePrompt: (body: PromoteRequest) =>
    post<PromptVersion>("/flywheel/prompt/promote", body),

  rollbackPrompt: (body: RollbackRequest) =>
    post<PromptVersion>("/flywheel/prompt/rollback", body),
};
