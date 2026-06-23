import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { SkillRoiResponse } from "@/types/flywheel";

// Mock the 13.0 client: the section is the only thing under test, not the fetch.
const { getSkillRoi } = vi.hoisted(() => ({ getSkillRoi: vi.fn() }));
vi.mock("@/services/flywheel", () => ({ flywheelService: { getSkillRoi } }));

import { SkillRoiSection } from "./SkillRoiSection";

afterEach(() => {
  cleanup(); // globals are off, so RTL's auto-cleanup isn't registered
  vi.clearAllMocks();
});

// Deliberately NOT sorted by roi: proves the component renders the server's order
// as-is and never re-ranks client-side (trap 3 — determinism).
const RESPONSE: SkillRoiResponse = {
  metric: "interview_lift",
  min_n: 5,
  skills: [
    {
      skill: "sql",
      roi: 0.12,
      n: 9,
      confidence: "strong_inference",
      contributing_signal_ids: ["sig-a", "sig-b"],
    },
    {
      skill: "python",
      roi: 0.88,
      n: 7,
      confidence: "strong_inference",
      contributing_signal_ids: ["sig-c"],
    },
    {
      skill: "rust",
      roi: 0.5,
      n: 2,
      confidence: "weak_inference",
      contributing_signal_ids: ["sig-d"],
    },
  ],
  // Server-computed: only strong + roi>0. `rust` (weak, low-n) is excluded.
  recommended: ["sql", "python"],
};

test("renders skills in server rank order, without re-sorting by roi", async () => {
  getSkillRoi.mockResolvedValue(RESPONSE);
  render(<SkillRoiSection />);

  await waitFor(() => expect(screen.getAllByTestId("roi-skill")).toHaveLength(3));
  const order = screen.getAllByTestId("roi-skill").map((el) => el.textContent);
  expect(order).toEqual(["sql", "python", "rust"]);
});

test("low-n skill shows weak_inference and is NOT emphasized as recommended", async () => {
  getSkillRoi.mockResolvedValue(RESPONSE);
  render(<SkillRoiSection />);

  const rustRow = await screen.findByTestId("roi-row-rust");
  expect(within(rustRow).getByText(/weak/i)).toBeTruthy();
  expect(within(rustRow).queryByText(/recommended/i)).toBeNull();

  // A skill the server DID recommend carries the emphasis.
  const sqlRow = screen.getByTestId("roi-row-sql");
  expect(within(sqlRow).getByText(/recommended/i)).toBeTruthy();
});

test("every ROI row can expand to reveal its contributing signal ids", async () => {
  getSkillRoi.mockResolvedValue(RESPONSE);
  render(<SkillRoiSection />);

  const sqlRow = await screen.findByTestId("roi-row-sql");
  // Collapsed by default — no orphan ids on screen.
  expect(within(sqlRow).queryByText("sig-a")).toBeNull();

  fireEvent.click(within(sqlRow).getByRole("button", { name: /why/i }));

  expect(within(sqlRow).getByText("sig-a")).toBeTruthy();
  expect(within(sqlRow).getByText("sig-b")).toBeTruthy();
});

test("a row with no contributing ids still explains itself, not an orphan number", async () => {
  getSkillRoi.mockResolvedValue({
    metric: "interview_lift",
    min_n: 5,
    skills: [
      { skill: "go", roi: -0.1, n: 6, confidence: "weak_inference", contributing_signal_ids: [] },
    ],
    recommended: [],
  } satisfies SkillRoiResponse);
  render(<SkillRoiSection />);

  const row = await screen.findByTestId("roi-row-go");
  // Negative ROI renders without a leading "+".
  expect(within(row).getByText("-0.10")).toBeTruthy();
  fireEvent.click(within(row).getByRole("button", { name: /why/i }));
  expect(within(row).getByText(/no contributing signals/i)).toBeTruthy();
});

test("empty skills render the dormant state, never an error", async () => {
  getSkillRoi.mockResolvedValue({
    metric: "interview_lift",
    min_n: 5,
    skills: [],
    recommended: [],
  } satisfies SkillRoiResponse);
  render(<SkillRoiSection />);

  await waitFor(() => expect(screen.getByText(/not enough/i)).toBeTruthy());
  expect(screen.queryByText(/error/i)).toBeNull();
});
