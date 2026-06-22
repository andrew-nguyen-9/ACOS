import { test, expect } from "@playwright/test";
import type { Route } from "@playwright/test";

// Phase 11.6: virtualization, predictive warm(), and shared-element layout
// transitions. Self-sufficient — mocks onboarding/health so no live backend.
const json = (body: unknown) => (route: Route) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

const bigList = Array.from({ length: 500 }, (_, i) => ({
  id: `app-${i}`,
  company: `Company ${i}`,
  role: `Role ${i}`,
  status: ["applied", "interviewing", "offer", "rejected", "saved"][i % 5],
  created_at: "2026-06-19T10:00:00",
}));

const RANKINGS = {
  template_rankings: [
    { template_name: "Harvard Classic", win_rate: 0.42, avg_ats_score: 88, application_count: 12 },
    { template_name: "Modern Tech", win_rate: 0.31, avg_ats_score: 81, application_count: 9 },
  ],
  ats_vs_outcome: [{ signal_type: "interview", avg_ats_score: 85, count: 5 }],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
  await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
  await page.route(/\/api\/v1\/applications\/$/, json(bigList));
  await page.route("**/api/v1/learning/report", json(RANKINGS));
});

test("virtualized list renders only a window of rows and scrolls cleanly", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

  await page.goto("/applications");
  await expect(page.getByText("Role 0")).toBeVisible({ timeout: 8_000 });

  // 500 items, but virtualization keeps the DOM tiny.
  const rendered = await page.locator("[data-index]").count();
  expect(rendered).toBeGreaterThan(0);
  expect(rendered).toBeLessThan(60);

  // Scroll the virtual container to the end; far rows render, top rows recycle.
  const scroller = page.locator(".contain-paint").first();
  await scroller.evaluate((el) => (el.scrollTop = el.scrollHeight));
  await expect(page.getByText("Role 499")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText("Role 0")).toHaveCount(0); // recycled out of DOM

  // DOM node count stays bounded even at the bottom of a 500-row list.
  expect(await page.locator("[data-index]").count()).toBeLessThan(60);

  expect(errors).toEqual([]);
});

test("hovering a nav item warms its backend data (predictive prefetch)", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  const warmed = page.waitForRequest(
    (r) => /\/api\/v1\/applications\/$/.test(r.url()) && r.method() === "GET",
  );
  await page.getByRole("link", { name: "Applications CRM" }).hover();
  await warmed; // resolves only if the warm() GET fired on hover
});

test("clicking a ranking expands it into a shared-element detail card", async ({ page }) => {
  await page.goto("/learning");
  // The ranking row is the <span>; the template name also appears as the Avg
  // ATS card subtitle (a <div>), so scope to the row span.
  const row = page.locator("span", { hasText: /^Harvard Classic$/ });
  await expect(row).toBeVisible({ timeout: 8_000 });

  await row.click();
  // The detail overlay's Close button + detail-only label confirm the expansion.
  await expect(page.getByRole("button", { name: "Close" })).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText("Avg ATS", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("button", { name: "Close" })).toBeHidden();
});
