/**
 * Phase 14.2 — typed client for the local-only drift/observability routes.
 *
 * Mirrors backend/api/v1/routes/observability.py. Drift is computed off the hot
 * path (on read of /drift; the snapshot is an explicit POST), so a fetch-on-mount
 * is fine — no cache layer. No external telemetry: this is all local.
 */
import { apiFetch } from "./api";

export type DriftConfidence = "verified" | "strong_inference" | "weak_inference";

export interface DriftMetric {
  kind: string;
  baseline: number | null;
  current: number | null;
  delta: number | null;
  threshold: number;
  drifting: boolean;
  samples: number;
  confidence: DriftConfidence | null;
  baseline_version: string | null;
}

export interface SnapshotResult {
  recorded: string[];
  success_rate: number | null;
  outcomes: number;
}

export const observabilityService = {
  getDrift: () => apiFetch<{ metrics: DriftMetric[] }>("/observability/drift"),
  snapshot: () =>
    apiFetch<SnapshotResult>("/observability/drift/snapshot", { method: "POST" }),
};
