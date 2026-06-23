import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ConfidenceBadge } from "./ConfidenceBadge";

// The badge is the trust gate for every generated figure (ADR-006). All three
// levels must render, and weak_inference must be visibly distinct so a user is
// never misled into treating a model guess as fact.
test("renders all three ADR-006 levels", () => {
  const { rerender } = render(<ConfidenceBadge level="verified" />);
  expect(screen.getByText(/verified/i)).toBeTruthy();
  rerender(<ConfidenceBadge level="strong_inference" />);
  expect(screen.getByText(/strong/i)).toBeTruthy();
  rerender(<ConfidenceBadge level="weak_inference" />);
  expect(screen.getByText(/weak/i)).toBeTruthy();
});

test("weak_inference is visibly distinct from the trustworthy levels", () => {
  const { container: weak } = render(<ConfidenceBadge level="weak_inference" />);
  const { container: strong } = render(<ConfidenceBadge level="strong_inference" />);
  const weakClass = weak.firstElementChild?.className ?? "";
  const strongClass = strong.firstElementChild?.className ?? "";
  expect(weakClass).not.toBe(strongClass);
  // a warning marker on weak, absent on strong
  expect(weak.textContent).toMatch(/⚠/);
  expect(strong.textContent ?? "").not.toMatch(/⚠/);
});
