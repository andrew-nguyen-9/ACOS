import { afterEach, expect, test, vi } from "vitest";
import { flywheelService } from "./flywheel";
import type {
  GlobalRoiResponse,
  PromptVersion,
  SkillRoiResponse,
  StrategyRecommendation,
  TrialResult,
} from "@/types/flywheel";

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

test("getSkillRoi parses the ranked-skills shape and passes query params", async () => {
  const payload: SkillRoiResponse = {
    metric: "interview_lift",
    min_n: 5,
    skills: [
      {
        skill: "python",
        roi: 0.42,
        n: 7,
        confidence: "strong_inference",
        contributing_signal_ids: ["s1", "s2"],
      },
    ],
    recommended: ["python"],
  };
  mockJson(payload);

  const res = await flywheelService.getSkillRoi({ metric: "interview_lift", min_n: 5 });

  expect(res).toEqual(payload);
  const [url, init] = lastCall();
  expect(String(url)).toContain("/flywheel/skills/roi");
  expect(String(url)).toContain("metric=interview_lift");
  expect(String(url)).toContain("min_n=5");
  expect(init?.method ?? "GET").toBe("GET");
});

test("query builder omits params whose value is undefined", async () => {
  mockJson({ metric: "interview_lift", min_n: 5, skills: [], recommended: [] });
  await flywheelService.getSkillRoi({ metric: undefined, min_n: 5 });
  const url = String(lastCall()[0]);
  expect(url).toContain("min_n=5");
  expect(url).not.toContain("metric=");
});

test("getStrategy parses the recommendation shape and posts target_jd in the body", async () => {
  const payload: StrategyRecommendation = {
    industry: "technology",
    section_order: ["summary", "skills", "experience"],
    recommended_skills: ["python"],
    keyword_targets: ["python", "aws"],
    confidence: "strong_inference",
    flagged: false,
    evidence: ["s1"],
    global_suggestions: [],
    notes: "Grounded in the tenant's own outcome signals.",
  };
  mockJson(payload);

  const res = await flywheelService.getStrategy("Senior Python role");

  expect(res).toEqual(payload);
  // TRAP 5: the JD travels in a POST body, never the URL — a long pasted JD as a
  // query param blows the URL/header limit (414). The URL stays param-free.
  const [url, init] = lastCall();
  expect(String(url)).toContain("/flywheel/strategy");
  expect(String(url)).not.toContain("target_jd");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual({ target_jd: "Senior Python role" });
});

test("getGlobalRoi parses cross-tenant rankings", async () => {
  const payload: GlobalRoiResponse = {
    metric: "interview_lift",
    rankings: [
      {
        industry: "technology",
        skill: "python",
        roi: 0.3,
        tenant_count: 6,
        confidence: "strong_inference",
      },
    ],
  };
  mockJson(payload);

  const res = await flywheelService.getGlobalRoi();
  expect(res).toEqual(payload);
});

test("getGlobalRoi treats a k-anonymity-suppressed (empty) ranking as a normal result, not an error", async () => {
  // ADR-009: when no industry/skill clears k contributing tenants, the gate drops
  // every row and the route returns an empty list. The client must return it cleanly.
  const payload: GlobalRoiResponse = { metric: "interview_lift", rankings: [] };
  mockJson(payload);

  const res = await flywheelService.getGlobalRoi({ metric: "interview_lift" });
  expect(res.rankings).toEqual([]);
});

test("proposePrompt POSTs the proposal body and parses the version row", async () => {
  const payload: PromptVersion = {
    id: "v-123",
    prompt_name: "resume_bullet",
    version: "2",
    is_active: false,
    parent_version: "1",
    change_rationale: "lift from signals",
  };
  mockJson(payload);

  const body = {
    prompt_name: "resume_bullet",
    proposed_content: "...",
    signal_ids: ["s1"],
    rationale: "r",
    expected_impact: "i",
  };
  const res = await flywheelService.proposePrompt(body);

  expect(res).toEqual(payload);
  const [url, init] = lastCall();
  expect(String(url)).toContain("/flywheel/prompt/propose");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body))).toEqual(body);
});

test("trialPrompt parses the experiment result", async () => {
  const payload: TrialResult = { experiment_id: "e1", name: "trial", status: "running" };
  mockJson(payload);

  const res = await flywheelService.trialPrompt({ prompt_name: "resume_bullet", version: "2" });
  expect(res).toEqual(payload);
  expect(String(lastCall()[0])).toContain("/flywheel/prompt/trial");
});

test("promotePrompt POSTs approval and parses the activated version", async () => {
  const payload: PromptVersion = {
    id: "v-123",
    prompt_name: "resume_bullet",
    version: "2",
    is_active: true,
    parent_version: "1",
    change_rationale: null,
  };
  mockJson(payload);

  const res = await flywheelService.promotePrompt({
    prompt_name: "resume_bullet",
    version: "2",
    approved_by: "andrew",
  });
  expect(res).toEqual(payload);
  const [url, init] = lastCall();
  expect(String(url)).toContain("/flywheel/prompt/promote");
  expect(JSON.parse(String(init?.body)).approved_by).toBe("andrew");
});

test("rollbackPrompt parses the reverted version", async () => {
  const payload: PromptVersion = {
    id: "v-100",
    prompt_name: "resume_bullet",
    version: "1",
    is_active: true,
    parent_version: null,
    change_rationale: null,
  };
  mockJson(payload);

  const res = await flywheelService.rollbackPrompt({ prompt_name: "resume_bullet" });
  expect(res).toEqual(payload);
  expect(String(lastCall()[0])).toContain("/flywheel/prompt/rollback");
});
