import { test, expect } from "@playwright/test";
import type { Route } from "@playwright/test";

// Phase 11.6 perf gate (11.0 budgets): scrolling a ~500-item virtualized list
// must produce 0 long tasks (>50ms), and a modal fling-dismiss must stay smooth.
// Run headless via Playwright; metrics are logged for PERFORMANCE_LOG.md.
const json = (body: unknown) => (route: Route) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

const bigList = Array.from({ length: 500 }, (_, i) => ({
  id: `app-${i}`, company: `Company ${i}`, role: `Role ${i}`,
  status: ["applied", "interviewing", "offer", "rejected", "saved"][i % 5],
  created_at: "2026-06-19T10:00:00",
}));

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
  await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
  await page.route(/\/api\/v1\/applications\/$/, json(bigList));
});

test("scrolling 500 virtualized rows produces 0 long tasks", async ({ page }) => {
  await page.goto("/applications");
  await expect(page.getByText("Role 0")).toBeVisible({ timeout: 8_000 });

  const metrics = await page.evaluate(async (sel) => {
    const el = document.querySelector(sel) as HTMLElement;
    let longTasks = 0;
    const po = new PerformanceObserver((l) => { longTasks += l.getEntries().length; });
    po.observe({ entryTypes: ["longtask"] });

    let frames = 0;
    let raf = requestAnimationFrame(function tick() { frames++; raf = requestAnimationFrame(tick); });

    const total = el.scrollHeight - el.clientHeight;
    const T = 2000;
    const t0 = performance.now();
    await new Promise<void>((res) => {
      const step = () => {
        const p = Math.min(1, (performance.now() - t0) / T);
        el.scrollTop = (p < 0.5 ? p * 2 : (1 - p) * 2) * total; // down then back up
        if (p < 1) requestAnimationFrame(step); else res();
      };
      requestAnimationFrame(step);
    });

    const elapsed = performance.now() - t0;
    cancelAnimationFrame(raf);
    po.disconnect();
    return { longTasks, fps: Math.round((frames / elapsed) * 1000), domRows: document.querySelectorAll("[data-index]").length };
  }, ".contain-paint");

  console.log("[PERF 11.6] scroll:", JSON.stringify(metrics));
  expect(metrics.longTasks).toBe(0);
  expect(metrics.domRows).toBeLessThan(60);
});

test("modal fling-dismiss produces 0 long tasks", async ({ page }) => {
  await page.goto("/applications");
  await page.getByRole("button", { name: /Add Application/i }).first().click();
  const modal = page.locator(".cursor-grab").first();
  await expect(modal).toBeVisible();

  const box = (await modal.boundingBox())!;
  await page.evaluate(() => {
    (window as unknown as { __lt: number }).__lt = 0;
    new PerformanceObserver((l) => {
      (window as unknown as { __lt: number }).__lt += l.getEntries().length;
    }).observe({ entryTypes: ["longtask"] });
  });

  // Fast downward fling: press, accelerate down, release (carries velocity).
  await page.mouse.move(box.x + box.width / 2, box.y + 20);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) {
    await page.mouse.move(box.x + box.width / 2, box.y + 20 + i * 60, { steps: 1 });
  }
  await page.mouse.up();
  await page.waitForTimeout(600); // let the exit spring settle

  const longTasks = await page.evaluate(() => (window as unknown as { __lt: number }).__lt);
  console.log("[PERF 11.6] fling longTasks:", longTasks);
  expect(longTasks).toBe(0);
});
