import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { PromptVersionsResponse } from "@/types/flywheel";

// Mock the 13.0/13.4 client — the review UI is under test, not the transport.
const { getPromptVersions, promotePrompt, rollbackPrompt } = vi.hoisted(() => ({
  getPromptVersions: vi.fn(),
  promotePrompt: vi.fn(),
  rollbackPrompt: vi.fn(),
}));
vi.mock("@/services/flywheel", () => ({
  flywheelService: { getPromptVersions, promotePrompt, rollbackPrompt },
}));

import { PromptReview } from "./PromptReview";

const DATA: PromptVersionsResponse = {
  prompt_name: "resume/extract_keywords",
  active_version: "v1",
  versions: [
    { id: "a", version: "v1", is_active: true, parent_version: "v0", change_rationale: "original", created_at: "t0" },
    { id: "b", version: "v2", is_active: false, parent_version: "v1", change_rationale: "v1 underperforms | signals: sigA", created_at: "t1" },
  ],
  audit: [
    { action: "applied", old_value: "v0", new_value: "v1", actor: "andrew", created_at: "t0" },
  ],
  experiments: [],
};

beforeEach(() => {
  getPromptVersions.mockResolvedValue(DATA);
  promotePrompt.mockResolvedValue({});
  rollbackPrompt.mockResolvedValue({});
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("promotion is gated: the promote button is disabled until an approver is named", async () => {
  render(<PromptReview />);
  const btn = (await screen.findByTestId("promote-v2")) as HTMLButtonElement;
  expect(btn.disabled).toBe(true); // deliberate human act — no approver, no promote

  fireEvent.change(screen.getByTestId("approver-input"), { target: { value: "andrew" } });
  expect(btn.disabled).toBe(false);
});

test("approving sends the explicit approved_by (never auto-filled)", async () => {
  render(<PromptReview />);
  await screen.findByTestId("promote-v2");
  fireEvent.change(screen.getByTestId("approver-input"), { target: { value: "andrew" } });
  fireEvent.click(screen.getByTestId("promote-v2"));

  await waitFor(() =>
    expect(promotePrompt).toHaveBeenCalledWith({
      prompt_name: "resume/extract_keywords",
      version: "v2",
      approved_by: "andrew",
    }),
  );
});

test("rollback is one action that restores the prior active version", async () => {
  render(<PromptReview />);
  fireEvent.click(await screen.findByTestId("rollback"));
  await waitFor(() =>
    expect(rollbackPrompt).toHaveBeenCalledWith(
      expect.objectContaining({ prompt_name: "resume/extract_keywords" }),
    ),
  );
});

test("the active incumbent is marked LIVE and candidates are not", async () => {
  render(<PromptReview />);
  const liveRow = await screen.findByTestId("version-row-v1");
  expect(liveRow.textContent).toMatch(/live/i);
  const candRow = screen.getByTestId("version-row-v2");
  expect(candRow.textContent).toMatch(/candidate/i);
});

test("the audit trail renders recorded transitions", async () => {
  render(<PromptReview />);
  await waitFor(() => expect(screen.getAllByTestId("audit-row")).toHaveLength(1));
  expect(screen.getByText(/andrew/)).toBeTruthy();
});
