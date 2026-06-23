import { BASE, apiFetch, ApiError } from "@/services/api";
import type { IngestJob, OnboardingSummary } from "@/types/onboarding";

const TERMINAL = new Set(["done", "failed"]);

/**
 * Upload a document to the existing validated ingestion endpoint.
 *
 * Uses raw fetch (not apiFetch) because apiFetch hard-codes
 * `Content-Type: application/json`, which would clobber the multipart boundary
 * the browser must set for a FormData body.
 */
export async function ingestDocument(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<{ job_id: string }>;
}

export function getIngestStatus(jobId: string): Promise<IngestJob> {
  return apiFetch<IngestJob>(`/ingest/${jobId}`);
}

export function getOnboardingSummary(): Promise<OnboardingSummary> {
  return apiFetch<OnboardingSummary>("/onboarding/summary");
}

/**
 * Poll a job to a terminal state. Ingestion is short, so a poll is simpler than
 * wiring an EventSource lifecycle into the wizard.
 * ponytail: poll, swap to the SSE stream if large-file builds make this feel slow.
 */
export async function pollIngest(
  jobId: string,
  onUpdate: (job: IngestJob) => void,
  opts: { intervalMs?: number; maxAttempts?: number } = {},
): Promise<IngestJob> {
  const { intervalMs = 800, maxAttempts = 150 } = opts;
  for (let i = 0; i < maxAttempts; i++) {
    const job = await getIngestStatus(jobId);
    onUpdate(job);
    if (TERMINAL.has(job.status)) return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { job_id: jobId, status: "failed", error: "Timed out waiting for ingestion" };
}
