import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

const { pullModel } = vi.hoisted(() => ({ pullModel: vi.fn() }));
vi.mock("@/services/ollama", () => ({ pullModel }));

import { ModelPull } from "./ModelPull";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("download is consent-gated: a button is shown, no auto-pull", () => {
  render(<ModelPull model="qwen3:8b" onDone={() => {}} />);
  expect(screen.getByTestId("pull-button")).toBeTruthy();
  expect(pullModel).not.toHaveBeenCalled();
});

test("clicking download streams progress then calls onDone", async () => {
  pullModel.mockImplementation(async (_m, onProgress) => {
    onProgress({ completed: 50, total: 100 });
  });
  const onDone = vi.fn();
  render(<ModelPull model="qwen3:8b" onDone={onDone} />);
  fireEvent.click(screen.getByTestId("pull-button"));
  await waitFor(() => expect(screen.getByTestId("pull-done")).toBeTruthy());
  expect(onDone).toHaveBeenCalledTimes(1);
});

test("a failed pull surfaces an error and offers retry (degraded, not a crash)", async () => {
  pullModel.mockRejectedValueOnce(new Error("ollama unreachable"));
  render(<ModelPull model="qwen3:8b" onDone={() => {}} />);
  fireEvent.click(screen.getByTestId("pull-button"));
  await waitFor(() => expect(screen.getByText(/ollama unreachable/)).toBeTruthy());
  expect(screen.getByText(/Retry download/)).toBeTruthy();
});
