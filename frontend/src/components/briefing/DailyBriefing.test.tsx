import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { DailyBriefing } from "./DailyBriefing";
import { briefingService } from "@/services/briefing";
import type { DailyBriefing as Briefing } from "@/types/briefing";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const EMPTY: Briefing = {
  generated_at: "2026-06-23T00:00:00Z",
  goal: null,
  jobs_to_apply: [],
  skill_gaps: [],
  resume_adjustments: [],
  ats_opportunities: [],
  follow_ups: [],
};

function renderWith(data: Briefing) {
  vi.spyOn(briefingService, "get").mockResolvedValue(data);
  return render(
    <MemoryRouter>
      <DailyBriefing />
    </MemoryRouter>,
  );
}

test("empty briefing shows honest dormant sections, never fabricated items", async () => {
  renderWith(EMPTY);
  await waitFor(() => expect(screen.getByText(/daily briefing/i)).toBeTruthy());
  expect(screen.getByText(/no goal set yet/i)).toBeTruthy();
  // every section renders its dormant empty state
  expect(screen.getAllByText(/nothing here yet/i).length).toBe(5);
});

test("jobs carry confidence and flag off-goal recommendations", async () => {
  renderWith({
    ...EMPTY,
    goal: { category: "data_analytics", interview_probability: 0.5, confidence: "strong_inference", sample_size: 6 },
    jobs_to_apply: [
      {
        application_id: "a1", company: "DataCo", position: "Analyst", recommendation: "apply",
        fit_score: 82, confidence: "strong_inference", category: "data_analytics", aligned_to_goal: true,
      },
      {
        application_id: "a2", company: "OffCo", position: "PM", recommendation: "tailor",
        fit_score: 60, confidence: "weak_inference", category: "product_management", aligned_to_goal: false,
      },
    ],
  });
  await waitFor(() => expect(screen.getByText(/dataco/i)).toBeTruthy());
  // a confidence badge per job (never a bare verdict), and the off-goal flag
  expect(screen.getAllByText(/strong/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/off-goal/i)).toBeTruthy();
});
