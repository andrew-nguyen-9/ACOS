/**
 * Phase 15.4 — typed client for the daily briefing read surface.
 * Off the hot path: a single GET that rolls up the existing engines (ADR-012).
 */
import { apiFetch } from "./api";
import type { DailyBriefing } from "@/types/briefing";

export const briefingService = {
  get: () => apiFetch<DailyBriefing>("/briefing"),
};
