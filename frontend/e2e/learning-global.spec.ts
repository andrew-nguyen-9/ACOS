import { test, expect } from "./fixtures";

// Phase 13.3: the Global-Patterns section renders inside the Learning Engine,
// framed as cross-tenant SUGGESTIONS (ADR-009). Self-sufficient — mocks the
// flywheel + learning endpoints so it needs no live backend.
test.describe("Global patterns (Phase 13.3)", () => {
  test.beforeEach(async ({ page }) => {
    const json = (body: unknown) => (route: import("@playwright/test").Route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/applications**", json([]));
    // Non-empty report: LearningPage early-returns an empty state when there are
    // no template rankings, which would unmount the whole right column (this section).
    await page.route("**/api/v1/learning/report", json({ template_rankings: [{ template_name: "Classic", win_rate: 0.4, avg_ats_score: 82, application_count: 5 }], ats_vs_outcome: [] }));
    // Skill ROI shares the page; keep it dormant so this spec isolates 13.3.
    await page.route("**/api/v1/flywheel/skills/roi**", json({ metric: "interview_lift", min_n: 5, skills: [], recommended: [] }));
  });

  test("k>=5: renders cross-tenant suggestions with tenant counts and confidence, framed as advisory", async ({ page }) => {
    await page.route("**/api/v1/flywheel/global/roi**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          metric: "interview_lift",
          rankings: [
            { industry: "technology", skill: "kubernetes", roi: 0.21, tenant_count: 12, confidence: "strong_inference" },
            { industry: "technology", skill: "terraform", roi: 0.64, tenant_count: 8, confidence: "weak_inference" },
          ],
        }),
      }),
    );

    await page.goto("/learning");
    await expect(page.getByRole("heading", { name: "Global Patterns" })).toBeVisible();

    // Advisory framing — a suggestion, never a directive.
    await expect(page.getByText(/consider these against your own/i)).toBeVisible();

    const row = page.getByTestId("global-row-kubernetes");
    await expect(row.getByText(/12 tenants/i)).toBeVisible();
    await expect(row.getByText(/strong/i)).toBeVisible();
    // Aggregate only — no tenant identity anywhere on the surface.
    await expect(page.getByText(/tenant-[0-9a-f]/i)).toHaveCount(0);
  });

  test("k<5: the surface is dormant by design, not an error", async ({ page }) => {
    await page.route("**/api/v1/flywheel/global/roi**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ metric: "interview_lift", rankings: [] }),
      }),
    );

    await page.goto("/learning");
    await expect(page.getByRole("heading", { name: "Global Patterns" })).toBeVisible();
    await expect(page.getByText(/at least five profiles/i)).toBeVisible();
    await expect(page.getByText(/error/i)).toHaveCount(0);
  });
});
