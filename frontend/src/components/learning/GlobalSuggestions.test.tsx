import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { GlobalRoiResponse } from "@/types/flywheel";

// Mock the 13.0 client: the section is under test, not the fetch.
const { getGlobalRoi } = vi.hoisted(() => ({ getGlobalRoi: vi.fn() }));
vi.mock("@/services/flywheel", () => ({ flywheelService: { getGlobalRoi } }));

import { GlobalSuggestions } from "./GlobalSuggestions";

afterEach(() => {
  cleanup(); // globals are off, so RTL's auto-cleanup isn't registered
  vi.clearAllMocks();
});

// Deliberately NOT sorted by roi: proves the component renders the server's
// order as-is and never re-ranks client-side (determinism).
const RESPONSE: GlobalRoiResponse = {
  metric: "interview_lift",
  rankings: [
    { industry: "technology", skill: "kubernetes", roi: 0.21, tenant_count: 12, confidence: "strong_inference" },
    { industry: "technology", skill: "terraform", roi: 0.64, tenant_count: 8, confidence: "weak_inference" },
  ],
};

test("k<5 suppression renders the dormant state, never an error", async () => {
  // ADR-009: k-anonymity suppresses every candidate → rankings is [].
  getGlobalRoi.mockResolvedValue({ metric: "interview_lift", rankings: [] } satisfies GlobalRoiResponse);
  render(<GlobalSuggestions />);

  await waitFor(() => expect(screen.getByText(/not enough/i)).toBeTruthy());
  expect(screen.queryByText(/error/i)).toBeNull();
  // No suggestion rows leak through the dormant path.
  expect(screen.queryByTestId("global-skill")).toBeNull();
});

test("renders rankings in server order, without re-sorting by roi", async () => {
  getGlobalRoi.mockResolvedValue(RESPONSE);
  render(<GlobalSuggestions />);

  await waitFor(() => expect(screen.getAllByTestId("global-skill")).toHaveLength(2));
  const order = screen.getAllByTestId("global-skill").map((el) => el.textContent);
  // roi would put terraform (0.64) first; server order keeps kubernetes first.
  expect(order).toEqual(["kubernetes", "terraform"]);
});

test("each row carries its tenant COUNT and confidence, framed as a suggestion not a directive", async () => {
  getGlobalRoi.mockResolvedValue(RESPONSE);
  render(<GlobalSuggestions />);

  const row = await screen.findByTestId("global-row-kubernetes");
  // tenant_count is an aggregate count, never ids (no re-identification, ADR-009).
  expect(within(row).getByText(/12 tenants/i)).toBeTruthy();
  expect(within(row).getByText(/strong/i)).toBeTruthy();

  // Advisory framing: "consider", never a directive. Global suggests; local decides.
  expect(screen.getByText(/consider/i)).toBeTruthy();
  expect(screen.queryByText(/you must|always use|required/i)).toBeNull();
});

test("a single contributing tenant is described without leaking which one", async () => {
  getGlobalRoi.mockResolvedValue({
    metric: "interview_lift",
    rankings: [
      { industry: "finance", skill: "sql", roi: 0.3, tenant_count: 1, confidence: "weak_inference" },
    ],
  } satisfies GlobalRoiResponse);
  render(<GlobalSuggestions />);

  const row = await screen.findByTestId("global-row-sql");
  // Singular grammar, still only a count — no tenant identity.
  expect(within(row).getByText(/1 tenant\b/i)).toBeTruthy();
});
