import { test, expect } from "./fixtures";

// Phase 13.1: the Skill-ROI section renders inside the Learning Engine page,
// ranked + confidence-tagged + explainable. Self-sufficient — mocks the flywheel
// and learning endpoints so it doesn't need a live backend.
test.describe("Skill ROI (Phase 13.1)", () => {
  test.beforeEach(async ({ page }) => {
    const json = (body: unknown) => (route: import("@playwright/test").Route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/applications**", json([]));
    await page.route("**/api/v1/learning/report", json({ template_rankings: [{ template_name: "Classic", win_rate: 0.4, avg_ats_score: 82, application_count: 5 }], ats_vs_outcome: [] }));
    await page.route("**/api/v1/flywheel/skills/roi**", json({
      metric: "interview_lift",
      min_n: 5,
      skills: [
        { skill: "python", roi: 0.88, n: 7, confidence: "strong_inference", contributing_signal_ids: ["sig-c"] },
        { skill: "rust", roi: 0.5, n: 2, confidence: "weak_inference", contributing_signal_ids: ["sig-d"] },
      ],
      recommended: ["python"],
    }));
  });

  test("renders ranked, recommended-emphasized, explainable ROI rows", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });

    await page.goto("/learning");
    await expect(page.getByRole("heading", { name: "Skill ROI" })).toBeVisible();

    // Recommended skill carries the emphasis chip; the weak/low-n one does not.
    const pythonRow = page.getByTestId("roi-row-python");
    await expect(pythonRow.getByText(/recommended/i)).toBeVisible();
    const rustRow = page.getByTestId("roi-row-rust");
    await expect(rustRow.getByText(/weak/i)).toBeVisible();
    await expect(rustRow.getByText(/recommended/i)).toHaveCount(0);

    // Explainability: expand reveals the contributing signal ids.
    await expect(pythonRow.getByText("sig-c")).toHaveCount(0);
    await pythonRow.getByRole("button", { name: /why/i }).click();
    await expect(pythonRow.getByText("sig-c")).toBeVisible();

    expect(errors).toEqual([]);
  });
});
