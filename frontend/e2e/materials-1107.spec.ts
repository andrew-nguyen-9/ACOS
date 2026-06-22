import { test, expect } from "./fixtures";
import type { Route } from "@playwright/test";

// Phase 11.7: the WebGL material canvas mounts behind the shell on the Full tier
// and is absent on Off, with no console/WebGL errors either way. Self-sufficient
// — mocks onboarding/health so it needs no live backend.
const json = (body: unknown) => (route: Route) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

test.describe("WebGL material (Phase 11.7)", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/settings", json({ settings: {} }));
  });

  test("mounts exactly one canvas on the Full tier with no errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.addInitScript(() => localStorage.setItem("acos:visual-effects", "full"));
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Lazy three chunk loads → one shared background canvas appears (HAM-001).
    await expect(page.locator("canvas")).toHaveCount(1);
    expect(errors).toEqual([]);
  });

  test("renders fully with no canvas when effects are Off", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.addInitScript(() => localStorage.setItem("acos:visual-effects", "off"));
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    await expect(page.locator("canvas")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test("Settings tier toggle persists and drives the canvas live", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("acos:visual-effects", "full"));
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(page.locator("canvas")).toHaveCount(1);

    // Turn effects Off → canvas unmounts live, preference persists.
    await page.getByRole("button", { name: "Off", exact: true }).click();
    await expect(page.locator("canvas")).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.getItem("acos:visual-effects"))).toBe("off");

    // Back to Full → the lazy canvas comes back.
    await page.getByRole("button", { name: "Full", exact: true }).click();
    await expect(page.locator("canvas")).toHaveCount(1);
  });
});
