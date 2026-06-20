import { test, expect } from "./fixtures";

test.describe("Cover Letter Generation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/cover-letters");
  });

  test("page loads with textarea and Generate Cover Letter button", async ({
    page,
  }) => {
    await expect(
      page.getByPlaceholder("Paste the job description…")
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Generate Cover Letter/i })
    ).toBeVisible();
  });

  test("Generate Cover Letter button is disabled when job description is empty", async ({
    page,
  }) => {
    await expect(
      page.getByRole("button", { name: /Generate Cover Letter/i })
    ).toBeDisabled();
  });

  test("generates a cover letter and displays content text", async ({
    page,
  }) => {
    await page
      .getByPlaceholder("Paste the job description…")
      .fill("Software Engineer at Acme Corp");

    await page.getByRole("button", { name: /Generate Cover Letter/i }).click();
    await page.waitForResponse("**/api/v1/cover-letter/generate");

    // MOCK content_text starts with "Dear Hiring Manager"
    await expect(page.getByText(/Dear Hiring Manager/i)).toBeVisible({
      timeout: 8_000,
    });
    // "I am excited to apply" is unique to the response content (not the textarea)
    await expect(page.getByText(/I am excited to apply/i)).toBeVisible();
  });

  test("shows error container on API failure", async ({ page }) => {
    await page.unroute("**/api/v1/cover-letter/generate");
    await page.route("**/api/v1/cover-letter/generate", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "text/plain",
        body: "LLM unavailable",
      });
    });

    await page
      .getByPlaceholder("Paste the job description…")
      .fill("Python role");
    await page.getByRole("button", { name: /Generate Cover Letter/i }).click();

    await expect(page.locator(".bg-red-500\\/10")).toBeVisible({ timeout: 8_000 });
  });
});
