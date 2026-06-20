import { apiFetch } from "./api";

export interface Proposal {
  id: string;
  target_engine: string;
  target_parameter: string;
  current_value: string | null;
  proposed_value: string;
  rationale: string;
  expected_impact: string;
  confidence_level: "verified" | "strong_inference" | "weak_inference";
  risk_level: "low" | "medium" | "high";
  evidence_json: string | null;
  status: "pending" | "approved" | "rejected" | "reverted";
  created_at: string;
  updated_at: string;
  decided_at: string | null;
}

export interface OptimizationLog {
  id: string;
  proposal_id: string | null;
  action: "applied" | "reverted";
  target_engine: string;
  target_parameter: string;
  old_value: string | null;
  new_value: string | null;
  actor: string;
  created_at: string;
}

export interface ABVariant {
  id: string;
  label: string;
  impressions: number;
  conversions: number;
  conversion_rate: number;
}

export interface ABExperiment {
  id: string;
  name: string;
  target_engine: string;
  metric: string;
  status: "running" | "concluded";
  winner_variant_id: string | null;
  created_at: string;
  concluded_at: string | null;
  variants: ABVariant[];
}

export interface PromptVersion {
  id: string;
  prompt_name: string;
  version: string;
  is_active: boolean;
  parent_version: string | null;
  change_rationale: string | null;
  created_at: string;
}

export async function listProposals(status?: string): Promise<Proposal[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  const data = await apiFetch<{ proposals: Proposal[] }>(`/optimization/proposals${q}`);
  return data.proposals;
}

export async function generateProposals(): Promise<{ created: number; proposal_ids: string[] }> {
  return apiFetch("/optimization/proposals/generate", { method: "POST" });
}

export async function approveProposal(id: string): Promise<Proposal> {
  return apiFetch(`/optimization/proposals/${id}/approve`, { method: "POST" });
}

export async function rejectProposal(id: string): Promise<Proposal> {
  return apiFetch(`/optimization/proposals/${id}/reject`, { method: "POST" });
}

export async function applyProposal(id: string): Promise<OptimizationLog> {
  return apiFetch(`/optimization/proposals/${id}/apply`, { method: "POST" });
}

export async function revertProposal(id: string): Promise<OptimizationLog> {
  return apiFetch(`/optimization/proposals/${id}/revert`, { method: "POST" });
}

export async function listLogs(limit = 50): Promise<OptimizationLog[]> {
  const data = await apiFetch<{ logs: OptimizationLog[] }>(`/optimization/logs?limit=${limit}`);
  return data.logs;
}

export async function runLoop(): Promise<{ ran: boolean; [k: string]: unknown }> {
  return apiFetch("/optimization/loop/run", { method: "POST" });
}

export async function listExperiments(): Promise<ABExperiment[]> {
  const data = await apiFetch<{ experiments: ABExperiment[] }>("/optimization/experiments");
  return data.experiments;
}

export async function createExperiment(payload: {
  name: string;
  target_engine: string;
  variant_a: Record<string, unknown>;
  variant_b: Record<string, unknown>;
}): Promise<{ experiment_id: string; variant_ids: Record<string, string> }> {
  return apiFetch("/optimization/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function concludeExperiment(id: string): Promise<ABExperiment> {
  return apiFetch(`/optimization/experiments/${id}/conclude`, { method: "POST" });
}

export async function listPromptVersions(name: string): Promise<PromptVersion[]> {
  const data = await apiFetch<{ versions: PromptVersion[] }>(
    `/optimization/prompts/${name}/versions`,
  );
  return data.versions;
}

export async function seedPrompt(name: string): Promise<PromptVersion> {
  return apiFetch(`/optimization/prompts/${name}/seed`, { method: "POST" });
}

export async function activatePromptVersion(id: string): Promise<PromptVersion> {
  return apiFetch(`/optimization/prompts/versions/${id}/activate`, { method: "POST" });
}
