import { test, expect } from "./fixtures";

// Phase 13.4: the prompt-evolution review queue renders inside the Optimization
// page — approval-gated promote, one-click rollback, audit trail. Self-sufficient:
// mocks the flywheel + optimization endpoints so it needs no live backend.
test.describe("Prompt Evolution Review (Phase 13.4)", () => {
  test.beforeEach(async ({ page }) => {
    const json = (body: unknown) => (route: import("@playwright/test").Route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/optimization/proposals**", json({ proposals: [] }));
    await page.route("**/api/v1/optimization/logs**", json({ logs: [] }));
    await page.route("**/api/v1/flywheel/prompt/versions**", json({
      prompt_name: "resume/extract_keywords",
      active_version: "v1",
      versions: [
        { id: "a", version: "v1", is_active: true, parent_version: "v0", change_rationale: "original", created_at: "t0" },
        { id: "b", version: "v2", is_active: false, parent_version: "v1", change_rationale: "v1 underperforms | signals: sigA", created_at: "t1" },
      ],
      audit: [{ action: "applied", old_value: "v0", new_value: "v1", actor: "andrew", created_at: "t0" }],
      experiments: [],
    }));
    await page.route("**/api/v1/flywheel/prompt/promote", json({ id: "b", version: "v2", is_active: true }));
  });

  test("promotion is approval-gated; incumbent is LIVE; audit renders", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });
    page.on("dialog", (d) => void d.accept()); // accept the destructive-action confirm

    await page.goto("/optimization");
    await expect(page.getByRole("heading", { name: "Prompt Evolution Review" })).toBeVisible();

    // The active incumbent is clearly LIVE; the candidate is not.
    await expect(page.getByTestId("version-row-v1")).toContainText(/live/i);
    await expect(page.getByTestId("version-row-v2")).toContainText(/candidate/i);

    // Promote is disabled until an approver is named (deliberate human act).
    const promote = page.getByTestId("promote-v2");
    await expect(promote).toBeDisabled();
    await page.getByTestId("approver-input").fill("andrew");
    await expect(promote).toBeEnabled();

    // Promote fires (confirm accepted) and the queue re-loads without error.
    await promote.click();
    await expect(page.getByTestId("version-row-v1")).toBeVisible();

    // Audit trail shows the recorded transition.
    await expect(page.getByTestId("audit-row")).toHaveCount(1);
    await expect(page.getByTestId("audit-row")).toContainText("andrew");

    expect(errors).toEqual([]);
  });
});
