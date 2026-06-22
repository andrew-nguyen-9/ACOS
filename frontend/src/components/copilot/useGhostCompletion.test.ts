import { describe, it, expect } from "vitest";
import { ghostReducer, initialGhost } from "./useGhostCompletion";

describe("ghostReducer (COP-003 Tab/Esc state machine)", () => {
  it("shows a non-empty suggestion", () => {
    const s = ghostReducer(initialGhost, { type: "suggest", suggestion: " by 40%" });
    expect(s).toEqual({ suggestion: " by 40%", status: "showing" });
  });

  it("treats an empty suggestion as idle", () => {
    const s = ghostReducer(initialGhost, { type: "suggest", suggestion: "" });
    expect(s.status).toBe("idle");
    expect(s.suggestion).toBe("");
  });

  it("accept clears the ghost and returns to idle", () => {
    const showing = ghostReducer(initialGhost, { type: "suggest", suggestion: " by 40%" });
    const s = ghostReducer(showing, { type: "accept" });
    expect(s).toEqual({ suggestion: "", status: "idle" });
  });

  it("dismiss clears the ghost and locks out further suggestions", () => {
    const showing = ghostReducer(initialGhost, { type: "suggest", suggestion: " by 40%" });
    const dismissed = ghostReducer(showing, { type: "dismiss" });
    expect(dismissed).toEqual({ suggestion: "", status: "dismissed" });

    // A suggestion arriving while dismissed is ignored — no ghost flicker.
    const stillDismissed = ghostReducer(dismissed, { type: "suggest", suggestion: " more" });
    expect(stillDismissed).toEqual({ suggestion: "", status: "dismissed" });
  });

  it("input change re-enables suggestions after a dismiss", () => {
    const dismissed = ghostReducer(
      ghostReducer(initialGhost, { type: "suggest", suggestion: " x" }),
      { type: "dismiss" },
    );
    const reset = ghostReducer(dismissed, { type: "input" });
    expect(reset.status).toBe("idle");

    const shown = ghostReducer(reset, { type: "suggest", suggestion: " y" });
    expect(shown).toEqual({ suggestion: " y", status: "showing" });
  });
});
