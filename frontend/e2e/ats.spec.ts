import { test, expect } from "./fixtures";

test.describe("ATS Scoring", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/ats");
  });

  test("page loads with textarea and Analyze Match button", async ({ page }) => {
    await expect(
      page.getByPlaceholder("Paste the job description to analyze keyword match…")
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Analyze Match/i })
    ).toBeVisible();
  });

  test("Analyze Match button is disabled when job description is empty", async ({
    page,
  }) => {
    await expect(
      page.getByRole("button", { name: /Analyze Match/i })
    ).toBeDisabled();
  });

  test("ATS scoring returns score and keyword sections", async ({ page }) => {
    await page
      .getByPlaceholder("Paste the job description to analyze keyword match…")
      .fill("Data Engineer role requiring Python, SQL, ETL skills.");

    await page.getByRole("button", { name: /Analyze Match/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    // Score circles render the value as plain text; overall_score=85 from mock
    await expect(page.getByText("85")).toBeVisible({ timeout: 8_000 });
    // Matched keyword pill — scoped to a <span> to avoid textarea content
    await expect(
      page.locator("span").filter({ hasText: /^Python$/ }).first()
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.locator("span").filter({ hasText: /^ETL$/ }).first()
    ).toBeVisible();
  });

  test("shows Matched Keywords and Missing Keywords headings", async ({
    page,
  }) => {
    await page
      .getByPlaceholder("Paste the job description to analyze keyword match…")
      .fill("Python data engineer role");
    await page.getByRole("button", { name: /Analyze Match/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    await expect(page.getByText(/Matched Keywords/i)).toBeVisible({
      timeout: 8_000,
    });
    await expect(page.getByText(/Missing Keywords/i)).toBeVisible();
  });

  test("shows error container on API failure", async ({ page }) => {
    await page.unroute("**/api/v1/resume/generate");
    await page.route("**/api/v1/resume/generate", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "text/plain",
        body: "LLM unavailable",
      });
    });

    await page
      .getByPlaceholder("Paste the job description to analyze keyword match…")
      .fill("Python role");
    await page.getByRole("button", { name: /Analyze Match/i }).click();

    await expect(page.locator(".bg-red-500\\/10")).toBeVisible({ timeout: 8_000 });
  });
});
