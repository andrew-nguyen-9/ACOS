import { test, expect } from "./fixtures";
import type { Route } from "@playwright/test";

// Phase 11.9 capstones. Self-sufficient — mocks onboarding/health/settings and
// forces effects Off so WebGL never loads in the browser run (the particle +
// interlocutor GL are covered by the manual perf gate, not here). With effects
// Off, the celebration degrades to the CelebrationFallback, the tone dial still
// morphs typography client-side, and the interview page still builds its audio
// graph + panel UI — exactly the "Off tier is fully usable" guarantee.
const json = (body: unknown) => (route: Route) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

const QUESTIONS = {
  questions: [
    {
      id: "q1",
      application_id: "app-uuid-1234-5678-9012-345678901234",
      question_text: "Tell me about a hard technical decision.",
      difficulty: "medium",
      question_type: "behavioral",
    },
  ],
};

test.describe("Showcase capstones (Phase 11.9)", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/settings/onboarding", json({ completed: true }));
    await page.route("**/api/v1/health/ollama", json({ degraded: false, available: true, missing_models: [] }));
    await page.route("**/api/v1/settings", json({ settings: {} }));
    await page.route("**/api/v1/questions/generate", json(QUESTIONS));
    await page.route("**/api/v1/learning/outcome", json({ recorded: true }));
    await page.addInitScript(() => localStorage.setItem("acos:visual-effects", "off"));
  });

  test("finalizing a strong resume fires a (skippable) celebration", async ({ page }) => {
    await page.goto("/resumes");
    await page.getByPlaceholder("Paste the full job description here…").fill("Python ETL engineer");
    await page.getByRole("button", { name: /Generate Resume/i }).click();

    // Off tier → the celebration degrades to the non-blocking fallback flourish.
    const flourish = page.getByText("Nicely done.");
    await expect(flourish).toBeVisible();
    // Skippable / non-blocking: it does not trap interaction and auto-dismisses.
    await expect(flourish).toBeHidden({ timeout: 4_000 });
  });

  test("tone dial morphs the cover letter with no console errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto("/cover-letters");
    await page.getByPlaceholder("Paste the job description…").fill("Senior PM role");
    await page.getByRole("button", { name: /Generate Cover Letter/i }).click();

    const dial = page.getByLabel("Cover letter tone: Traditional to Bold");
    await expect(dial).toBeVisible();
    await dial.fill("0.9"); // drag toward Bold → instant typography morph
    await expect(page.getByText(/Dear Hiring Manager/)).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("interview page builds the audio panel with no errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));

    await page.goto("/interview-prep");
    await page.getByRole("combobox").selectOption({ label: "Software Engineer at Acme Corp" });
    await page.getByRole("button", { name: /Generate Questions/i }).click();

    // The Web Audio panel materializes (analyser active) → seats + cadence meter.
    await expect(page.getByText("Virtual Panel")).toBeVisible();
    await expect(page.getByText("Recruiter")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
