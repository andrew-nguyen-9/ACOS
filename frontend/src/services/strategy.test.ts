import { afterEach, expect, test, vi } from "vitest";
import { strategyService } from "./strategy";
import type { ApplicationPriority } from "@/types/strategy";

function mockJson(payload: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(payload)))),
  );
}

function lastCall() {
  return (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit?];
}

afterEach(() => vi.unstubAllGlobals());

test("prioritize POSTs the jobs body and parses the ranked shape", async () => {
  const payload: ApplicationPriority[] = [
    {
      job_id: "job-1",
      jd_snippet: "Senior Data Analyst…",
      priority: "tailor",
      reason: "Good fit (65/100).",
      fit_score: 65,
      confidence: "strong_inference",
      missing_critical_skills: ["dbt"],
      risk_factors: [],
      explanation: "Moderate fit.",
      top_pick: true,
    },
  ];
  mockJson(payload);

  const res = await strategyService.prioritize([{ job_id: "job-1", jd_text: "x".repeat(60) }]);

  expect(res).toEqual(payload);
  const [url, init] = lastCall();
  // JD is large → body, never a query param.
  expect(String(url)).toContain("/strategy/prioritize");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toHaveProperty("jobs");
});
