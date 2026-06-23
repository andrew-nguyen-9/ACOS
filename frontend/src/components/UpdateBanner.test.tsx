import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

const { checkForUpdate } = vi.hoisted(() => ({ checkForUpdate: vi.fn() }));
vi.mock("@/services/updater", () => ({ checkForUpdate }));

import { UpdateBanner } from "./UpdateBanner";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("renders nothing when there is no update", async () => {
  checkForUpdate.mockResolvedValue(null);
  render(<UpdateBanner />);
  await waitFor(() => expect(checkForUpdate).toHaveBeenCalled());
  expect(screen.queryByTestId("update-banner")).toBeNull();
});

test("shows the version + release notes and installs on click", async () => {
  const install = vi.fn().mockResolvedValue(undefined);
  checkForUpdate.mockResolvedValue({ version: "0.2.0", notes: "Fixes the thing", install });
  render(<UpdateBanner />);

  expect(await screen.findByTestId("update-banner")).toBeTruthy();
  expect(screen.getByText(/v0\.2\.0/)).toBeTruthy();
  expect(screen.getByTestId("update-notes").textContent).toContain("Fixes the thing");

  fireEvent.click(screen.getByTestId("update-install"));
  await waitFor(() => expect(install).toHaveBeenCalledTimes(1));
});

test("a failed update surfaces an error without crashing", async () => {
  const install = vi.fn().mockRejectedValue(new Error("signature verification failed"));
  checkForUpdate.mockResolvedValue({ version: "0.2.0", notes: "", install });
  render(<UpdateBanner />);

  fireEvent.click(await screen.findByTestId("update-install"));
  await waitFor(() => expect(screen.getByText(/signature verification failed/)).toBeTruthy());
});
