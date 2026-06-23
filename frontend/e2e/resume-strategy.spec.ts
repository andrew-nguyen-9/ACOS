import { test, expect } from "./fixtures";

// Phase 13.2: optional, non-blocking strategy hints in the resume editor. The
// fixtures auto-mock resume/generate; here we mock POST /flywheel/strategy so
// the suite needs no live backend.
test.describe("Resume strategy hints (Phase 13.2)", () => {
  // Clear the onboarding gate so /resumes renders without a live backend.
  test.beforeEach(async ({ page }) => {
    const json = (body: unknown) => (route: import("@playwright/test").Route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
  });

  const fillAndGenerate = async (page: import("@playwright/test").Page) => {
    await page.goto("/resumes");
    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python Data Engineer at Acme. Requires Python, SQL, ETL.");
    await page.getByRole("button", { name: /Generate Resume/i }).click();
    // No waitForResponse here: the mock fulfills instantly and a post-click
    // listener can miss it. Each test waits on a resulting UI signal instead.
  };

  test("renders confidence-tagged, section-tied hints from the server recommendation", async ({ page }) => {
    await page.route("**/api/v1/flywheel/strategy", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          industry: "technology",
          section_order: ["summary", "skills", "experience"],
          recommended_skills: ["python", "aws"],
          keyword_targets: ["etl"],
          confidence: "strong_inference",
          flagged: false,
          evidence: ["sig-a"],
          global_suggestions: [],
          notes: "Grounded in the tenant's own outcome signals.",
        }),
      }),
    );

    await fillAndGenerate(page);

    await expect(page.getByText("Strategy hints")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("Strong")).toBeVisible();
    await expect(page.getByText("aws")).toBeVisible();
    await expect(page.getByText(/own outcome signals/i)).toBeVisible();

    // Dismissible — the editor keeps working without it.
    await page.getByRole("button", { name: /dismiss strategy hints/i }).click();
    await expect(page.getByText("Strategy hints")).toHaveCount(0);
    await expect(page.getByText(/ATS 85/)).toBeVisible();
  });

  test("unknown industry shows a flag, never a guessed industry (TRAP 3)", async ({ page }) => {
    await page.route("**/api/v1/flywheel/strategy", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          industry: "unknown",
          section_order: ["summary", "experience"],
          recommended_skills: [],
          keyword_targets: [],
          confidence: "weak_inference",
          flagged: true,
          evidence: [],
          global_suggestions: [],
          notes: "Industry not matched — generic guidance.",
        }),
      }),
    );

    await fillAndGenerate(page);

    await expect(page.getByText(/unverified industry/i)).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText(/tuned for/i)).toHaveCount(0);
  });

  test("perf gate: the hint surface adds no long tasks across render + dismiss", async ({ page }) => {
    await page.route("**/api/v1/flywheel/strategy", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          industry: "technology",
          section_order: ["summary", "skills", "experience", "education", "projects"],
          recommended_skills: ["python", "aws", "sql", "etl", "spark"],
          keyword_targets: ["python", "etl", "airflow", "dbt"],
          confidence: "strong_inference",
          flagged: false,
          evidence: ["s1", "s2", "s3"],
          global_suggestions: [],
          notes: "Grounded in the tenant's own outcome signals.",
        }),
      }),
    );

    await page.goto("/resumes");
    // Install a long-task observer before interacting.
    await page.evaluate(() => {
      (window as unknown as { __longTasks: number }).__longTasks = 0;
      new PerformanceObserver((list) => {
        (window as unknown as { __longTasks: number }).__longTasks += list.getEntries().length;
      }).observe({ entryTypes: ["longtask"] });
    });

    await page
      .getByPlaceholder("Paste the full job description here…")
      .fill("Python Data Engineer at Acme. Requires Python, SQL, ETL.");
    await page.getByRole("button", { name: /Generate Resume/i }).click();
    await expect(page.getByText("Strategy hints")).toBeVisible({ timeout: 8_000 });

    // Zero the counter AFTER the hint has mounted: the generate render itself is
    // pre-existing app work (BulletXRay portals, EvidencePanel, LazyMotion). What
    // this gate attributes to 13.2 is the hint's own interaction — the dismiss.
    await page.evaluate(() => {
      (window as unknown as { __longTasks: number }).__longTasks = 0;
    });
    await page.getByRole("button", { name: /dismiss strategy hints/i }).click();
    await expect(page.getByText("Strategy hints")).toHaveCount(0);

    const longTasks = await page.evaluate(
      () => (window as unknown as { __longTasks: number }).__longTasks,
    );
    expect(longTasks).toBe(0);
  });

  test("editor works identically when the hints fetch fails — hints are non-blocking", async ({ page }) => {
    await page.route("**/api/v1/flywheel/strategy", (route) =>
      route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }),
    );

    await fillAndGenerate(page);

    // The resume still renders; no strategy surface appears.
    await expect(page.getByText(/ATS 85/)).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("Data Engineer — Acme Corp")).toBeVisible();
    await expect(page.getByText("Strategy hints")).toHaveCount(0);
  });
});
