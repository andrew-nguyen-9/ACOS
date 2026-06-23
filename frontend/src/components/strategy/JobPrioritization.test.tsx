import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { JobPrioritization } from "./JobPrioritization";
import { strategyService } from "@/services/strategy";
import type { ApplicationPriority } from "@/types/strategy";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const ROWS: ApplicationPriority[] = [
  {
    job_id: "job-1", jd_snippet: "A", priority: "prioritize", reason: "High fit.",
    fit_score: 88, confidence: "strong_inference", missing_critical_skills: [],
    risk_factors: [], explanation: "Strong fit.", top_pick: true,
  },
  {
    job_id: "job-2", jd_snippet: "B", priority: "skip", reason: "Low fit.",
    fit_score: 30, confidence: "weak_inference", missing_critical_skills: ["python"],
    risk_factors: ["Low skill overlap"], explanation: "Weak fit.", top_pick: false,
  },
];

async function runWith(rows: ApplicationPriority[]) {
  vi.spyOn(strategyService, "prioritize").mockResolvedValue(rows);
  render(<JobPrioritization />);
  fireEvent.change(screen.getByPlaceholderText(/paste a job description/i), {
    target: { value: "Some JD text here long enough." },
  });
  fireEvent.click(screen.getByRole("button", { name: /prioritize/i }));
}

test("renders rows in the server-provided order (no client re-rank)", async () => {
  await runWith(ROWS);
  await waitFor(() => expect(screen.getByText(/strong fit/i)).toBeTruthy());
  const reasons = screen.getAllByText(/fit\./i).map((n) => n.textContent);
  // job-1 (High fit) before job-2 (Low fit) — server order preserved.
  expect(reasons.findIndex((t) => /high/i.test(t ?? ""))).toBeLessThan(
    reasons.findIndex((t) => /low/i.test(t ?? "")),
  );
});

test("every recommendation carries a confidence badge — never a bare verdict", async () => {
  await runWith(ROWS);
  await waitFor(() => expect(screen.getByText(/strong fit/i)).toBeTruthy());
  expect(screen.getAllByText(/strong/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/weak/i).length).toBeGreaterThan(0);
});

test("top pick is marked and weak rows are not", async () => {
  await runWith(ROWS);
  await waitFor(() => expect(screen.getByText(/top pick/i)).toBeTruthy());
  // exactly one top-pick marker
  expect(screen.getAllByText(/top pick/i)).toHaveLength(1);
});

// ADR-012: the surface recommends, it never acts. No Apply/Submit/Contact button
// that would hit an external system may exist here.
test("exposes no outbound-action affordance (ADR-012 boundary)", async () => {
  await runWith(ROWS);
  await waitFor(() => expect(screen.getByText(/strong fit/i)).toBeTruthy());
  const buttons = screen.getAllByRole("button").map((b) => b.textContent?.toLowerCase() ?? "");
  for (const label of buttons) {
    expect(label).not.toMatch(/submit|apply now|contact|send|outreach|auto-apply/);
  }
});
