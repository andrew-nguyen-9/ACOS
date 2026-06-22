import { test, expect } from "./fixtures";
import type { Route } from "@playwright/test";

// Phase 11.8: signature features + theme sync. Self-sufficient — mocks
// onboarding/health and forces effects Off to keep WebGL out of the browser run
// (haptics + asset:// are native-only and covered by Rust tests, not here).
const json = (body: unknown) => (route: Route) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

test.describe("macOS integration + signature features (Phase 11.8)", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/settings", json({ settings: {} }));
    await page.addInitScript(() => localStorage.setItem("acos:visual-effects", "off"));
  });

  test("X-Ray popover reveals a bullet's structural math on hover", async ({ page }) => {
    await page.goto("/resumes");
    await expect(page.getByRole("heading", { name: "Resume Builder" })).toBeVisible();

    await page.getByPlaceholder("Paste the full job description here…").fill("Python ETL engineer");
    await page.getByRole("button", { name: "Generate Resume" }).click();

    // The X-Ray hover target is the underlined bullet span in the resume card
    // (the same text also appears in the evidence panel).
    const bullet = page.locator("span.cursor-help", {
      hasText: "Built Python ETL pipeline reducing costs by 40%",
    });
    await expect(bullet).toBeVisible();
    await bullet.hover();

    await expect(page.getByText("Impact X-Ray")).toBeVisible();
    await expect(page.getByText("Built", { exact: true })).toBeVisible(); // action verb
    await expect(page.getByText("40%", { exact: true })).toBeVisible(); // quantified metric chip
    await expect(page.getByText("2 matched")).toBeVisible(); // ATS keyword coverage
  });

  test("copilot ghost text appears and Tab accepts it", async ({ page }) => {
    await page.goto("/copilot");
    const input = page.getByPlaceholder("Ask your Career Copilot anything...");
    await expect(input).toBeVisible();
    await input.fill("Tell me about my Python experience");

    // Ghost completion streams the mocked chat reply as inline ghost text.
    const ghost = page.getByText(/Based on your experience/);
    await expect(ghost).toBeVisible();

    await input.press("Tab");
    await expect(input).toHaveValue(/Based on your experience/);
  });

  test("system theme change swaps the theme with no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Establish a dark baseline, then flip the OS to light → clip-path reveal.
    // (Spaced so the media transitions don't coalesce into a single net change.)
    await page.emulateMedia({ colorScheme: "dark" });
    await page.waitForTimeout(150);
    await page.emulateMedia({ colorScheme: "light" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    // …and back to dark removes the attribute (the true-dark default).
    await page.emulateMedia({ colorScheme: "dark" });
    await expect(page.locator("html")).not.toHaveAttribute("data-theme", "light");

    expect(errors).toEqual([]);
  });
});
