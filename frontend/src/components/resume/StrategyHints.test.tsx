import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { StrategyHints } from "./StrategyHints";
import type { StrategyRecommendation } from "@/types/flywheel";

// This repo's vitest config has no global setup/auto-cleanup; unmount per test
// so absence assertions don't see DOM left over from a prior render.
afterEach(cleanup);

const RICH: StrategyRecommendation = {
  industry: "technology",
  section_order: ["summary", "skills", "experience"],
  recommended_skills: ["python", "aws"],
  keyword_targets: ["python", "etl"],
  confidence: "strong_inference",
  flagged: false,
  evidence: ["sig-a", "sig-b"],
  global_suggestions: [],
  notes: "Grounded in the tenant's own outcome signals.",
};

test("rec=null renders nothing — the editor is byte-identical when hints are absent", () => {
  const { container } = render(<StrategyHints rec={null} />);
  expect(container.firstChild).toBeNull();
});

test("rich data renders a confident, section-tied hint as-is", () => {
  render(<StrategyHints rec={RICH} />);
  // Confidence is first-class (ADR-006): the server's level renders, no re-grading.
  expect(screen.getByText("Strong")).toBeTruthy();
  // Section-tied recommendations render verbatim — no client re-ranking.
  expect(screen.getByText("summary")).toBeTruthy();
  expect(screen.getByText("aws")).toBeTruthy();
  expect(screen.getByText("etl")).toBeTruthy();
  // The hint cites the tenant's own evidence (TRAP 2), not invented advice.
  expect(screen.getByText(/own outcome signals/i)).toBeTruthy();
});

test("sparse data renders the server's generic + weak_inference recommendation, no invented advice", () => {
  const sparse: StrategyRecommendation = {
    ...RICH,
    confidence: "weak_inference",
    recommended_skills: [],
    keyword_targets: [],
    evidence: [],
    notes: "Too few signals yet — generic guidance.",
  };
  render(<StrategyHints rec={sparse} />);
  expect(screen.getByText("Weak ⚠")).toBeTruthy();
  expect(screen.getByText(/generic guidance/i)).toBeTruthy();
});

test("unknown industry shows a flagged chip, never a guessed industry as advice (TRAP 3)", () => {
  const flagged: StrategyRecommendation = {
    ...RICH,
    industry: "unknown",
    flagged: true,
    confidence: "weak_inference",
  };
  render(<StrategyHints rec={flagged} />);
  expect(screen.getByText(/unverified industry/i)).toBeTruthy();
  // A flagged recommendation must NOT present its industry guess as a tuned label.
  expect(screen.queryByText(/tuned for/i)).toBeNull();
});

test("hints are dismissible", () => {
  render(<StrategyHints rec={RICH} />);
  fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
  expect(screen.queryByText("summary")).toBeNull();
});
