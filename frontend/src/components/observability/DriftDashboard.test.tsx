import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { DriftMetric } from "@/services/observability";

const { getDrift } = vi.hoisted(() => ({ getDrift: vi.fn() }));
vi.mock("@/services/observability", () => ({
  observabilityService: { getDrift },
}));

import { DriftDashboard } from "./DriftDashboard";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function metric(kind: string, over: Partial<DriftMetric>): DriftMetric {
  return {
    kind,
    baseline: null,
    current: null,
    delta: null,
    threshold: 0.15,
    drifting: false,
    samples: 0,
    confidence: null,
    baseline_version: null,
    ...over,
  };
}

test("renders a trend + confidence + versioned baseline for a drifting metric", async () => {
  getDrift.mockResolvedValue({
    metrics: [
      metric("ats_score", {
        baseline: 80,
        current: 60,
        delta: -20,
        samples: 12,
        drifting: true,
        confidence: "strong_inference",
        baseline_version: "0.1.0",
      }),
    ],
  });
  render(<DriftDashboard />);
  await waitFor(() => expect(screen.getByText("ATS accuracy")).toBeTruthy());
  expect(screen.getByText("60.00")).toBeTruthy();
  expect(screen.getByText(/from 80.00/)).toBeTruthy();
  expect(screen.getByText("drifting")).toBeTruthy();
  expect(screen.getByText("Strong")).toBeTruthy();
  expect(screen.getByText(/baseline v0.1.0/)).toBeTruthy();
});

test("low-n / no-confidence metric shows the dormant state, not a fake number", async () => {
  getDrift.mockResolvedValue({
    metrics: [metric("success_rate", { samples: 1, confidence: null })],
  });
  render(<DriftDashboard />);
  await waitFor(() =>
    expect(screen.getByText("Resume success rate")).toBeTruthy()
  );
  // dormant copy appears; no current value rendered
  expect(screen.getAllByText("Not enough data yet").length).toBeGreaterThan(0);
});
