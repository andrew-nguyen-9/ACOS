import { test, expect } from "./fixtures";

test.describe("Copilot Chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/copilot");
  });

  test("page loads with chat input and send button", async ({ page }) => {
    await expect(
      page.getByPlaceholder("Ask your Career Copilot anything...")
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Send message/i })
    ).toBeVisible();
  });

  test("send button is disabled when input is empty", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: /Send message/i })
    ).toBeDisabled();
  });

  test("sends a message and displays copilot response", async ({ page }) => {
    await page
      .getByPlaceholder("Ask your Career Copilot anything...")
      .fill("What Python work have I done?");
    await page.getByRole("button", { name: /Send message/i }).click();

    await page.waitForResponse("**/api/v1/copilot/chat");

    // MOCK_COPILOT_RESPONSE.response
    await expect(
      page.getByText(/strong Python and data engineering skills/i)
    ).toBeVisible({ timeout: 8_000 });
  });

  test("message input clears after sending", async ({ page }) => {
    const input = page.getByPlaceholder("Ask your Career Copilot anything...");
    await input.fill("What Python work have I done?");
    await page.getByRole("button", { name: /Send message/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    await expect(input).toHaveValue("", { timeout: 5_000 });
  });

  test("can send multiple messages in sequence", async ({ page }) => {
    const input = page.getByPlaceholder("Ask your Career Copilot anything...");

    await input.fill("First question");
    await page.getByRole("button", { name: /Send message/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    await input.fill("Second question");
    await page.getByRole("button", { name: /Send message/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    await expect(page.getByText("First question")).toBeVisible();
    await expect(page.getByText("Second question")).toBeVisible();
  });
});
