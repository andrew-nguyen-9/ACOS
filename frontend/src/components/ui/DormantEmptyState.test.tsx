import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { DormantEmptyState } from "./DormantEmptyState";

test("renders default dormant copy framing suppression as normal, not an error", () => {
  render(<DormantEmptyState />);
  // It must read as a calm "not enough data yet" state — never an error.
  expect(screen.getByText(/not enough/i)).toBeTruthy();
  expect(screen.queryByText(/error/i)).toBeNull();
});

test("accepts an override description for the specific suppressed surface", () => {
  render(<DormantEmptyState description="Global patterns unlock once 5 profiles contribute." />);
  expect(screen.getByText(/5 profiles contribute/i)).toBeTruthy();
});
