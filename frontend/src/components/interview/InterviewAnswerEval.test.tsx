import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { InterviewAnswerEval } from "./InterviewAnswerEval";
import { learningService } from "@/services/learning";
import type { AnswerEvaluation } from "@/types/api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const EVAL: AnswerEvaluation = {
  coverage: 0.67, covered_node_ids: ["n1", "n2"], missing_node_ids: ["n3"],
  matched_labels: ["Python", "ETL"], expected_count: 3, confidence: "strong_inference",
};

test("evaluation renders with a confidence badge and follow-ups — never a bare score", async () => {
  vi.spyOn(learningService, "evaluateAnswer").mockResolvedValue(EVAL);
  vi.spyOn(learningService, "getFollowups").mockResolvedValue({
    followups: ["Can you quantify the impact?", "What was the trade-off?"],
  });
  render(<InterviewAnswerEval questionText="Tell me about a project." persona="technical" />);

  fireEvent.change(screen.getByPlaceholderText(/type your answer/i), {
    target: { value: "I used Python to build ETL pipelines." },
  });
  fireEvent.click(screen.getByRole("button", { name: /evaluate/i }));

  await waitFor(() => expect(screen.getByText(/evidence coverage/i)).toBeTruthy());
  // grounded in named KG evidence + confidence-tagged (ADR-006)
  expect(screen.getAllByText(/python/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/strong/i)).toBeTruthy();
  expect(screen.getByText(/can you quantify/i)).toBeTruthy();
});

test("empty answer cannot be evaluated (no fabricated score)", () => {
  const evalSpy = vi.spyOn(learningService, "evaluateAnswer");
  render(<InterviewAnswerEval questionText="Q" />);
  expect((screen.getByRole("button", { name: /evaluate/i }) as HTMLButtonElement).disabled).toBe(true);
  expect(evalSpy).not.toHaveBeenCalled();
});

test("honest empty state when there is no graph to ground against", async () => {
  vi.spyOn(learningService, "evaluateAnswer").mockResolvedValue({
    coverage: 0, covered_node_ids: [], missing_node_ids: [], matched_labels: [],
    expected_count: 0, confidence: "weak_inference",
  });
  vi.spyOn(learningService, "getFollowups").mockResolvedValue({ followups: [] });
  render(<InterviewAnswerEval questionText="Q" />);
  fireEvent.change(screen.getByPlaceholderText(/type your answer/i), { target: { value: "x" } });
  fireEvent.click(screen.getByRole("button", { name: /evaluate/i }));
  await waitFor(() => expect(screen.getByText(/no knowledge-graph evidence/i)).toBeTruthy());
});
