import { test, expect } from "./fixtures";

// Phase 11.5: the revamped AppShell (material proxy) + Dashboard reference
// adoption render and navigate cleanly. Self-sufficient — mocks onboarding so it
// doesn't need a live backend.
test.describe("Dashboard shell (Phase 11.5)", () => {
  test.beforeEach(async ({ page }) => {
    const json = (body: unknown) => (route: import("@playwright/test").Route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
  });

  test("renders the dashboard and navigates without console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("Resumes Generated")).toBeVisible();

    // AppShell nav works (hover prefetch + click).
    await page.getByRole("link", { name: "Applications CRM" }).hover();
    await page.getByRole("link", { name: "Applications CRM" }).click();
    await expect(page).toHaveURL(/\/applications/);

    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    expect(errors).toEqual([]);
  });
});
