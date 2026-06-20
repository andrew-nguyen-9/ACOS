import { test, expect } from "./fixtures";

// Predicate matching the applications collection response
const isCollectionResponse = (r: { url: () => string; request: () => { method: () => string } }) =>
  /\/api\/v1\/applications\/$/.test(r.url()) && r.request().method() === "GET";

test.describe("Application CRM", () => {
  test.beforeEach(async ({ page }) => {
    // Set up the waitForResponse BEFORE goto so we don't miss the
    // response fired by useEffect on mount
    const responsePromise = page.waitForResponse(isCollectionResponse);
    await page.goto("/applications");
    await responsePromise;
  });

  test("page loads with Add Application button", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: /Add Application/i }).first()
    ).toBeVisible({ timeout: 8_000 });
  });

  test("shows applications list from API", async ({ page }) => {
    // MOCK returns Acme Corp / Software Engineer
    await expect(page.getByText("Acme Corp")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("Software Engineer")).toBeVisible();
  });

  test("shows applied status badge", async ({ page }) => {
    // STATUS_CONFIG["applied"].label = "Applied"
    await expect(page.getByText("Applied").first()).toBeVisible({
      timeout: 8_000,
    });
  });

  test("can open and fill Add Application modal", async ({ page }) => {
    // Before modal opens, only the header button exists — no index needed
    await page.getByRole("button", { name: /Add Application/i }).click();

    await expect(page.getByPlaceholder("Acme Corp")).toBeVisible();
    await expect(page.getByPlaceholder("Senior Engineer")).toBeVisible();
  });

  test("can submit a new application", async ({ page }) => {
    await page.getByRole("button", { name: /Add Application/i }).click();

    await page.getByPlaceholder("Acme Corp").fill("New Company");
    await page.getByPlaceholder("Senior Engineer").fill("Backend Engineer");

    // Modal renders first in DOM (inside .fixed overlay), so scope to it.
    // Both "Add Application" buttons exist when modal is open; .fixed scopes to the modal's.
    const postResponsePromise = page.waitForResponse(
      (r) => /\/api\/v1\/applications\//.test(r.url()) && r.request().method() === "POST"
    );
    await page.locator(".fixed").getByRole("button", { name: /Add Application/i }).click();
    await postResponsePromise;

    // After submit, modal closes; list has both the original and new entry
    await expect(page.getByText("Acme Corp").first()).toBeVisible({ timeout: 8_000 });
  });

  test("shows empty state when no applications", async ({ page }) => {
    // Add a higher-priority route that returns empty list (last-registered wins)
    await page.route(/\/api\/v1\/applications\//, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: "[]",
        });
      } else {
        await route.continue();
      }
    });

    const reloadResponsePromise = page.waitForResponse(isCollectionResponse);
    await page.reload();
    await reloadResponsePromise;

    await expect(
      page.getByText(/No applications yet/i)
    ).toBeVisible({ timeout: 8_000 });
  });
});
