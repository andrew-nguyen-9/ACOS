import { test, expect } from "./fixtures";

test.describe("Resume Generation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/resumes");
  });

  test("page loads with textarea and Generate Resume button", async ({ page }) => {
    await expect(
      page.getByPlaceholder("Paste the full job description here…")
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Generate Resume/i })
    ).toBeVisible();
  });

  test("Generate Resume button is disabled when job description is empty", async ({
    page,
  }) => {
    const btn = page.getByRole("button", { name: /Generate Resume/i });
    await expect(btn).toBeDisabled();
  });

  test("generates resume and displays ATS score and experience", async ({
    page,
  }) => {
    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python Data Engineer at Acme Corp. Requires Python, SQL, ETL.");

    await page.getByRole("button", { name: /Generate Resume/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    // ATS score badge: "ATS 85"
    await expect(page.getByText(/ATS 85/)).toBeVisible({ timeout: 8_000 });
    // Experience entry — exact heading text is "Data Engineer — Acme Corp"
    await expect(page.getByText("Data Engineer — Acme Corp")).toBeVisible();
    await expect(page.getByText(/ETL pipeline/i).first()).toBeVisible();
  });

  test("displays verified confidence badge after generation", async ({
    page,
  }) => {
    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python engineering role");
    await page.getByRole("button", { name: /Generate Resume/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    // ConfidenceBadge renders "Verified" (capital V) inside a <span> in a list item
    await expect(
      page.getByRole("listitem").getByText("Verified").first()
    ).toBeVisible({ timeout: 8_000 });
  });

  test("download .docx button appears after generation", async ({ page }) => {
    await page.route("**/api/v1/resume/generate/download", async (route) => {
      await route.fulfill({
        status: 200,
        contentType:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        body: Buffer.from("PK fake docx"),
      });
    });

    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python role");
    await page.getByRole("button", { name: /Generate Resume/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    // The download button shows ".docx"
    await expect(page.getByRole("button", { name: /\.docx/i })).toBeVisible({
      timeout: 8_000,
    });
  });

  test("shows error message on API failure", async ({ page }) => {
    await page.unroute("**/api/v1/resume/generate");
    await page.route("**/api/v1/resume/generate", async (route) => {
      await route.fulfill({
        status: 500,
        // Return plain text so ApiError.message is a simple string
        contentType: "text/plain",
        body: "Internal server error",
      });
    });

    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python role");
    await page.getByRole("button", { name: /Generate Resume/i }).click();

    // Error container (bg-red-500/10) becomes visible
    await expect(page.locator(".bg-red-500\\/10")).toBeVisible({ timeout: 8_000 });
  });
});
