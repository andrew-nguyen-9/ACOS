import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock("@/services/api", () => ({ apiFetch, ApiError: class extends Error {}, BASE: "" }));

const { updateSetting, completeOnboarding } = vi.hoisted(() => ({
  updateSetting: vi.fn(),
  completeOnboarding: vi.fn(),
}));
vi.mock("@/services/settings", () => ({ updateSetting, completeOnboarding }));

// Upload sub-step is exercised in UploadStep.test.tsx; stub it here so the skip
// path is what's under test.
vi.mock("@/components/onboarding/UploadStep", () => ({ UploadStep: () => null }));

import FirstRunWizard from "./FirstRunWizard";

beforeEach(() => {
  apiFetch.mockResolvedValue({ available: true, missing_models: [], degraded: false });
  updateSetting.mockResolvedValue(undefined);
  completeOnboarding.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("a user who uploads nothing can still complete onboarding", async () => {
  render(<FirstRunWizard onComplete={() => {}} />);

  fireEvent.click(screen.getByText("Begin Setup"));
  fireEvent.click(await screen.findByText("Continue")); // ollama → profile
  fireEvent.click(await screen.findByText("Finish Setup"));

  await waitFor(() => expect(completeOnboarding).toHaveBeenCalledTimes(1));
  expect(await screen.findByText("Setup complete!")).toBeTruthy();
});
