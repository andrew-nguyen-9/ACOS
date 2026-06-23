import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ApplicationSuggestion } from "./ApplicationSuggestion";
import { strategyService } from "@/services/strategy";
import { applicationsService } from "@/services/applications";
import type { Application } from "@/types/api";
import type { ApplicationSuggestion as Suggestion } from "@/types/strategy";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const APP: Application = {
  id: "a1", company: "Acme", role: "Data Analyst", status: "saved",
  date_applied: null, notes: null, job_description: "Python SQL data analyst role.",
  created_at: "", updated_at: "",
};

const SUGG: Suggestion = {
  recommendation: "tailor", reason: "Good fit (65/100).", fit_score: 65,
  confidence: "strong_inference", missing_critical_skills: ["dbt"], risk_factors: [],
  explanation: "Moderate fit.", resume_template: "data_technical",
  resume_reason: "Data role detected.", cover_letter_tone: 0.5,
  cover_letter_tone_descriptor: "balanced, professional, confident",
  interview_probability: 0.45, interview_sample_size: 2,
  interview_confidence: "weak_inference", interview_category: "data_analytics",
};

function mountWith() {
  vi.spyOn(strategyService, "suggest").mockResolvedValue(SUGG);
  return render(<ApplicationSuggestion app={APP} />);
}

test("renders resume, tone, and interview sections each confidence-tagged", async () => {
  mountWith();
  await waitFor(() => expect(screen.getByText(/data_technical/i)).toBeTruthy());
  expect(screen.getByText(/balanced, professional/i)).toBeTruthy();
  expect(screen.getByText(/interview likelihood/i)).toBeTruthy();
  // recommendation + interview outlook each carry a ConfidenceBadge (never bare).
  expect(screen.getByText(/strong/i)).toBeTruthy();
  expect(screen.getByText(/weak/i)).toBeTruthy();
});

test("missing JD shows a hint, not a fabricated suggestion", async () => {
  vi.spyOn(strategyService, "suggest").mockResolvedValue(SUGG);
  render(<ApplicationSuggestion app={{ ...APP, job_description: null }} />);
  expect(screen.getByText(/add a job description/i)).toBeTruthy();
  expect(strategyService.suggest).not.toHaveBeenCalled();
});

// ADR-012: Apply marks internal status — it must NOT submit to a job board.
test("Mark as applied calls the internal CRM update, not an external submit", async () => {
  mountWith();
  const update = vi
    .spyOn(applicationsService, "update")
    .mockResolvedValue({ ...APP, status: "applied" });
  await waitFor(() => expect(screen.getByText(/data_technical/i)).toBeTruthy());
  fireEvent.click(screen.getByRole("button", { name: /mark as applied/i }));
  await waitFor(() => expect(update).toHaveBeenCalledWith("a1", { status: "applied" }));
});

test("exposes no outbound-action affordance (ADR-012 boundary)", async () => {
  mountWith();
  await waitFor(() => expect(screen.getByText(/data_technical/i)).toBeTruthy());
  const labels = screen.getAllByRole("button").map((b) => b.textContent?.toLowerCase() ?? "");
  for (const label of labels) {
    expect(label).not.toMatch(/submit|contact|send|outreach|auto-apply|apply to job/);
  }
});
